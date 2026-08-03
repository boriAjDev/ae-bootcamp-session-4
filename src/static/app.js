document.addEventListener("DOMContentLoaded", () => {
  const capabilitiesList = document.getElementById("capabilities-list");
  const capabilitySelect = document.getElementById("capability");
  const registerForm = document.getElementById("register-form");
  const messageDiv = document.getElementById("message");
  const registerTitle = document.getElementById("register-title");
  const registerSubmit = document.getElementById("register-submit");
  const authStatus = document.getElementById("auth-status");
  const authButton = document.getElementById("auth-button");
  const loginModal = document.getElementById("login-modal");
  const loginForm = document.getElementById("login-form");
  const loginCancel = document.getElementById("login-cancel");
  const approvalsContainer = document.getElementById("approvals-container");
  const approvalsList = document.getElementById("approvals-list");

  let authUser = null;

  function isPracticeLead() {
    return Boolean(authUser && authUser.role === "practice_lead");
  }

  function showMessage(text, type = "info") {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");

    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function updateRoleBasedUI() {
    if (isPracticeLead()) {
      authStatus.textContent = `Signed in as ${authUser.username} (Practice Lead)`;
      authButton.textContent = "Sign Out";
      registerTitle.textContent = "Practice Lead Registration";
      registerSubmit.textContent = "Register Consultant";
      approvalsContainer.classList.remove("hidden");
      fetchPendingRequests();
    } else {
      authStatus.textContent = "Not signed in";
      authButton.textContent = "Practice Lead Login";
      registerTitle.textContent = "Request Capability Registration";
      registerSubmit.textContent = "Submit Request";
      approvalsContainer.classList.add("hidden");
    }
  }

  async function fetchSession() {
    try {
      const response = await fetch("/auth/session");
      const session = await response.json();
      authUser = session.authenticated ? session.user : null;
    } catch (error) {
      authUser = null;
      console.error("Failed to load session:", error);
    }

    updateRoleBasedUI();
  }

  // Function to fetch capabilities from API
  async function fetchCapabilities() {
    try {
      const response = await fetch("/capabilities");
      const capabilities = await response.json();

      // Clear loading message
      capabilitiesList.innerHTML = "";
      capabilitySelect.innerHTML = '<option value="">-- Select a capability --</option>';

      // Populate capabilities list
      Object.entries(capabilities).forEach(([name, details]) => {
        const capabilityCard = document.createElement("div");
        capabilityCard.className = "capability-card";

        const availableCapacity = details.capacity || 0;
        const currentConsultants = details.consultants ? details.consultants.length : 0;

        // Create consultants HTML with delete icons
        const consultantsHTML =
          details.consultants && details.consultants.length > 0
            ? `<div class="consultants-section">
              <h5>Registered Consultants:</h5>
              <ul class="consultants-list">
                ${details.consultants
                  .map(
                    (email) =>
                      `<li><span class="consultant-email">${email}</span>${
                        isPracticeLead()
                          ? `<button class="delete-btn" data-capability="${name}" data-email="${email}">Remove</button>`
                          : ""
                      }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No consultants registered yet</em></p>`;

        capabilityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Practice Area:</strong> ${details.practice_area}</p>
          <p><strong>Industry Verticals:</strong> ${details.industry_verticals ? details.industry_verticals.join(', ') : 'Not specified'}</p>
          <p><strong>Capacity:</strong> ${availableCapacity} hours/week available</p>
          <p><strong>Current Team:</strong> ${currentConsultants} consultants</p>
          <div class="consultants-container">
            ${consultantsHTML}
          </div>
        `;

        capabilitiesList.appendChild(capabilityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        capabilitySelect.appendChild(option);
      });

      if (isPracticeLead()) {
        document.querySelectorAll(".delete-btn").forEach((button) => {
          button.addEventListener("click", handleUnregister);
        });
      }
    } catch (error) {
      capabilitiesList.innerHTML =
        "<p>Failed to load capabilities. Please try again later.</p>";
      console.error("Error fetching capabilities:", error);
    }
  }

  async function fetchPendingRequests() {
    if (!isPracticeLead()) {
      return;
    }

    try {
      const response = await fetch("/registration-requests");
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Failed to load requests");
      }

      if (!payload.pending_requests || payload.pending_requests.length === 0) {
        approvalsList.innerHTML = "<p>No pending requests.</p>";
        return;
      }

      approvalsList.innerHTML = payload.pending_requests
        .map(
          (request) => `
            <div class="approval-card">
              <p><strong>${request.email}</strong> requested <strong>${request.capability_name}</strong></p>
              <div class="approval-actions">
                <button class="approve-btn" data-request-id="${request.id}">Approve</button>
                <button class="reject-btn" data-request-id="${request.id}">Reject</button>
              </div>
            </div>
          `
        )
        .join("");

      document.querySelectorAll(".approve-btn").forEach((button) => {
        button.addEventListener("click", () => handleReviewRequest(button, "approve"));
      });
      document.querySelectorAll(".reject-btn").forEach((button) => {
        button.addEventListener("click", () => handleReviewRequest(button, "reject"));
      });
    } catch (error) {
      approvalsList.innerHTML = `<p>Failed to load pending requests: ${error.message}</p>`;
    }
  }

  async function handleReviewRequest(button, action) {
    const requestId = button.getAttribute("data-request-id");

    try {
      const response = await fetch(`/registration-requests/${requestId}/${action}`, {
        method: "POST",
      });
      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        fetchCapabilities();
        fetchPendingRequests();
      } else {
        showMessage(result.detail || "Unable to update request", "error");
      }
    } catch (error) {
      showMessage("Unable to update request", "error");
      console.error("Request review error:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const capability = button.getAttribute("data-capability");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(
          capability
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");

        // Refresh capabilities list to show updated consultants
        fetchCapabilities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  authButton.addEventListener("click", async () => {
    if (isPracticeLead()) {
      try {
        await fetch("/auth/logout", { method: "POST" });
        authUser = null;
        updateRoleBasedUI();
        fetchCapabilities();
        showMessage("Signed out", "info");
      } catch (error) {
        showMessage("Unable to sign out", "error");
      }
      return;
    }

    loginModal.classList.remove("hidden");
  });

  loginCancel.addEventListener("click", () => {
    loginModal.classList.add("hidden");
    loginForm.reset();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();

      if (!response.ok) {
        showMessage(result.detail || "Login failed", "error");
        return;
      }

      authUser = result.user;
      loginModal.classList.add("hidden");
      loginForm.reset();
      updateRoleBasedUI();
      fetchCapabilities();
      showMessage("Practice lead signed in", "success");
    } catch (error) {
      showMessage("Login failed", "error");
    }
  });

  // Handle form submission
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const capability = document.getElementById("capability").value;

    try {
      const response = isPracticeLead()
        ? await fetch(
            `/capabilities/${encodeURIComponent(
              capability
            )}/register?email=${encodeURIComponent(email)}`,
            {
              method: "POST",
            }
          )
        : await fetch("/registration-requests", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, capability_name: capability }),
          });

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        registerForm.reset();

        if (isPracticeLead()) {
          fetchCapabilities();
        } else {
          fetchPendingRequests();
        }
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to submit. Please try again.", "error");
      console.error("Error registering:", error);
    }
  });

  // Initialize app
  fetchSession();
  fetchCapabilities();
});
