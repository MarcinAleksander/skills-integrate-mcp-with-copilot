document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const messageDiv = document.getElementById("message");
  const accountButton = document.getElementById("account-button");
  const accountMenu = document.getElementById("account-menu");
  const loginButton = document.getElementById("login-button");
  const accountDialog = document.getElementById("account-dialog");
  const closeDialogButton = document.getElementById("close-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  const teacherAccount = document.getElementById("teacher-account");
  const teacherName = document.getElementById("teacher-name");
  const logoutButton = document.getElementById("logout-button");
  let teacherUsername = null;

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  function updateAccountView() {
    const isTeacher = Boolean(teacherUsername);
    signupContainer.hidden = !isTeacher;
    accountButton.setAttribute(
      "aria-label",
      isTeacher ? "Teacher account" : "Teacher sign in"
    );
    accountButton.title = isTeacher ? "Teacher account" : "Teacher sign in";
    accountButton.setAttribute("aria-expanded", String(!accountMenu.classList.contains("hidden")));
    loginButton.classList.toggle("hidden", isTeacher);
    teacherAccount.classList.toggle("hidden", !isTeacher);
    teacherName.textContent = isTeacher
      ? `Signed in as ${teacherUsername}`
      : "";
    loginError.classList.add("hidden");
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;
        const safeName = escapeHtml(name);

        // Create participant rows with teacher-only unregister buttons.
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map((email) => {
                    const safeEmail = escapeHtml(email);
                    const unregisterButton = teacherUsername
                      ? `<button class="delete-btn" data-activity="${safeName}" data-email="${safeEmail}" aria-label="Unregister ${safeEmail}">Remove</button>`
                      : "";
                    return `<li><span class="participant-email">${safeEmail}</span>${unregisterButton}</li>`;
                  })
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${safeName}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  accountButton.addEventListener("click", () => {
    accountMenu.classList.toggle("hidden");
    accountButton.setAttribute(
      "aria-expanded",
      String(!accountMenu.classList.contains("hidden"))
    );
  });

  loginButton.addEventListener("click", () => {
    accountMenu.classList.add("hidden");
    accountButton.setAttribute("aria-expanded", "false");
    accountDialog.showModal();
  });

  closeDialogButton.addEventListener("click", () => {
    accountDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.classList.add("hidden");

    const formData = new FormData(loginForm);
    try {
      const response = await fetch("/auth/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to sign in");
      }

      teacherUsername = result.username;
      loginForm.reset();
      accountMenu.classList.add("hidden");
      updateAccountView();
      accountButton.setAttribute("aria-expanded", "false");
      accountDialog.close();
      await fetchActivities();
    } catch (error) {
      loginError.textContent = error.message || "Failed to sign in";
      loginError.classList.remove("hidden");
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/session", { method: "DELETE" });
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      teacherUsername = null;
      accountMenu.classList.add("hidden");
      updateAccountView();
      accountButton.setAttribute("aria-expanded", "false");
      await fetchActivities();
    } catch (error) {
      teacherName.textContent = `Failed to sign out: ${error.message}`;
    }
  });

  async function initialize() {
    try {
      const response = await fetch("/auth/session");
      if (response.ok) {
        const session = await response.json();
        teacherUsername = session.username;
      } else if (response.status !== 401) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      updateAccountView();
      await fetchActivities();
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to check teacher sign-in. Please reload the page.</p>";
      console.error("Error initializing app:", error);
    }
  }

  initialize();
});
