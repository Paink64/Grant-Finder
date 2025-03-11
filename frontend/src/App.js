import { useState, useEffect } from "react";
import { sendMessage } from "./api";

export default function App() {
  const [darkMode, setDarkMode] = useState(() => {
    return JSON.parse(localStorage.getItem("darkMode")) || false;
  });

  const [chats, setChats] = useState(() => {
    return (
      JSON.parse(localStorage.getItem("chats")) || [
        { id: 1, name: "New Chat", messages: [] },
      ]
    );
  });

  const [currentChatId, setCurrentChatId] = useState(chats[0]?.id || 1);
  const [input, setInput] = useState("");
  const [editingTitle, setEditingTitle] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  useEffect(() => {
    localStorage.setItem("chats", JSON.stringify(chats));
  }, [chats]);

  useEffect(() => {
    localStorage.setItem("darkMode", JSON.stringify(darkMode));
  }, [darkMode]);

  const currentChat = chats.find((chat) => chat.id === currentChatId);

  const handleSendMessage = async () => {
    if (!input.trim() || !currentChat) return;

    const userMessage = { role: "user", content: input };
    const response = await sendMessage("default", input);
    const botMessage = { role: "assistant", content: response };

    const updatedChats = chats.map((chat) =>
      chat.id === currentChatId
        ? { ...chat, messages: [...chat.messages, userMessage, botMessage] }
        : chat
    );

    setChats(updatedChats);
    setInput("");
  };

  const handleNewChat = () => {
    const newChat = {
      id: Date.now(),
      name: `Chat ${chats.length + 1}`,
      messages: [],
    };
    setChats([...chats, newChat]);
    setCurrentChatId(newChat.id);
  };

  const handleRenameChat = () => {
    if (!newTitle.trim()) return;

    const updatedChats = chats.map((chat) =>
      chat.id === currentChatId ? { ...chat, name: newTitle } : chat
    );

    setChats(updatedChats);
    setEditingTitle(false);
  };

  const handleDeleteChat = (chatId) => {
    const chatToDelete = chats.find((chat) => chat.id === chatId);

    if (
      window.confirm(`Are you sure you want to delete "${chatToDelete?.name}"?`)
    ) {
      const updatedChats = chats.filter((chat) => chat.id !== chatId);

      setChats(updatedChats);

      if (currentChatId === chatId) {
        setCurrentChatId(updatedChats.length ? updatedChats[0].id : null);
      }
    }
  };

  return (
    <div
      className={`flex h-screen w-screen ${
        darkMode ? "bg-gray-900 text-white" : "bg-gray-200 text-black"
      } transition-colors duration-300`}
    >
      {/* Sidebar Menu */}
      <div
        className={`w-64 p-4 flex flex-col ${
          darkMode ? "bg-gray-800 text-white" : "bg-white"
        } shadow-md transition-colors duration-300`}
      >
        <h2 className="text-lg font-bold mb-4">Chats</h2>

        <button
          className="w-full bg-blue-500 text-white p-2 rounded mb-2 hover:bg-blue-600"
          onClick={handleNewChat}
        >
          + New Chat
        </button>

        <div className="flex flex-col space-y-2">
          {chats.map((chat) => (
            <div key={chat.id} className="relative group">
              <button
                className={`p-2 rounded text-left w-full ${
                  currentChatId === chat.id
                    ? "bg-blue-300"
                    : darkMode
                    ? "hover:bg-gray-700"
                    : "hover:bg-gray-300"
                }`}
                onClick={() => setCurrentChatId(chat.id)}
              >
                {chat.name}
              </button>

              {/* Delete button appears on hover */}
              <button
                className="absolute right-2 top-2 hidden group-hover:block bg-red-500 text-white px-2 py-1 text-xs rounded"
                onClick={() => handleDeleteChat(chat.id)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex flex-col flex-grow h-full items-center justify-center">
        {/* Dark Mode Toggle */}
        <button
          className="absolute top-4 right-4 bg-gray-700 text-white px-4 py-2 rounded-lg shadow-md hover:bg-gray-600 transition"
          onClick={() => setDarkMode(!darkMode)}
        >
          {darkMode ? "Light Mode" : "Dark Mode"}
        </button>

        <div
          className={`flex flex-col h-full w-full max-w-2xl ${
            darkMode ? "bg-gray-800 text-white" : "bg-white"
          } shadow-md rounded-lg p-4 transition-colors duration-300`}
        >
          {/* Chat Title with Rename Option */}
          {editingTitle ? (
            <div className="flex items-center justify-center mb-2">
              <input
                type="text"
                className={`border p-1 rounded text-center ${
                  darkMode ? "text-black" : "text-black"
                }`}
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onBlur={handleRenameChat}
                onKeyDown={(e) => e.key === "Enter" && handleRenameChat()}
                autoFocus
              />
            </div>
          ) : (
            <h1
              className="text-xl font-bold mb-2 text-center cursor-pointer"
              onClick={() => {
                setEditingTitle(true);
                setNewTitle(currentChat?.name || "New Chat");
              }}
            >
              {currentChat?.name || "Chatbot"}
            </h1>
          )}

          {/* Chat Messages */}
          <div className="flex-grow overflow-y-auto border p-2 mb-2">
            {currentChat?.messages.map((msg, index) => (
              <div
                key={index}
                className={`p-2 rounded ${
                  msg.role === "user"
                    ? darkMode
                      ? "bg-blue-500 text-white"
                      : "bg-blue-200"
                    : darkMode
                    ? "bg-gray-700 text-white"
                    : "bg-gray-200"
                }`}
              >
                <strong>{msg.role === "user" ? "You" : "Bot"}:</strong>{" "}
                {msg.content}
              </div>
            ))}
          </div>

          {/* Input Box */}
          <div className="flex">
            <input
              type="text"
              className={`flex-grow border p-2 rounded ${
                darkMode ? "bg-gray-700 text-white border-gray-500" : ""
              }`}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
            />
            <button
              className="ml-2 bg-blue-500 text-white p-2 rounded"
              onClick={handleSendMessage}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
