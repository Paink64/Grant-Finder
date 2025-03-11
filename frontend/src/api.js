export const sendMessage = async (profile, message) => {
  try {
    const response = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ profile, message }),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch response from backend.");
    }

    const data = await response.json();
    return data.response || "Unexpected response from backend.";
  } catch (error) {
    console.error("Error:", error);
    return "Sorry, something went wrong!";
  }
};
