"use client";

import { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Menu, Send, PaperclipIcon, Home, Mic } from "lucide-react";
import ChatMessage from "./chat-message";
import Sidebar from "./sidebar";

export default function ChatInterface({ toggleSidebar, isLoggedIn }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [messages, setMessages] = useState(() => {
    // Check for passed state from history
    const location = useLocation();
    return (
      location.state?.messages || [
        {
          id: 1,
          content:
            "Hello!! I'm Dr MAMA, your medical assistant. How can I help you?",
          sender: "bot",
        },
      ]
    );
  });
  const [inputText, setInputText] = useState("");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Check if user is authenticated by verifying cookie or localStorage
  const checkAuthentication = () => {
    console.log("All cookies:", document.cookie); // Debug: see all cookies
    
    // Check if user cookie exists
    const userCookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith("user="));

    console.log("User cookie found:", userCookie); // Debug

    if (userCookie) {
      try {
        const userInfo = JSON.parse(decodeURIComponent(userCookie.split("=")[1]));
        console.log("Parsed user info from cookie:", userInfo); // Debug
        if (userInfo.user_id) {
          return true;
        }
      } catch (error) {
        console.error("Error parsing user cookie:", error);
      }
    }

    // Fallback: Check localStorage for user_id (in case cookie is not accessible)
    const userId = localStorage.getItem("user_id");
    console.log("User ID from localStorage:", userId); // Debug
    
    if (userId) {
      console.log("Authenticated via localStorage");
      return true;
    }

    console.log("No authentication found");
    return false;
  };

  const handleSendMessage = async () => {
    if (!inputText.trim() && selectedFiles.length === 0) return;

    // Check authentication before sending message
    if (!checkAuthentication()) {
      alert("Please sign in first to use the chatbot.");
      navigate("/signin");
      return;
    }

    const newMessage = {
      id: Date.now(),
      content: inputText,
      sender: "user",
      files: selectedFiles.length > 0 ? selectedFiles : undefined,
    };

    setMessages((prevMessages) => [...prevMessages, newMessage]);
    setIsLoading(true);

    try {
      console.log("Sending message:", inputText);

      // Get user_id for potential fallback
      const userId = localStorage.getItem("user_id");

      // Prepare request body - include user_id as fallback if backend needs it
      const requestBody = {
        message: inputText,
      };

      // If no cookie but have localStorage user_id, include it in body
      const userCookie = document.cookie
        .split("; ")
        .find((row) => row.startsWith("user="));

      if (!userCookie && userId) {
        requestBody.user_id = parseInt(userId, 10);
        console.log(
          "No cookie found, including user_id in request body:",
          requestBody.user_id
        );
      }

      const response = await fetch("http://localhost:8002/rag/query_rag/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include", // This is important for cookies
        body: JSON.stringify(requestBody),
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        if (response.status === 401) {
          // Clear any stored auth data and redirect to login
          document.cookie =
            "user=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
          localStorage.removeItem("access_token");
          localStorage.removeItem("token");
          localStorage.removeItem("authToken");
          localStorage.removeItem("user_id");
          alert("Your session has expired. Please sign in again.");
          navigate("/signin");
          return;
        }

        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }

      const data = await response.json();
      console.log("Response data:", data);

      const botResponse = {
        id: Date.now() + 1,
        content:
          data.response ||
          data.message ||
          "I received your message but couldn't generate a proper response.",
        sender: "bot",
      };

      setMessages((prevMessages) => [...prevMessages, botResponse]);
    } catch (error) {
      console.error("Error:", error);

      let errorMessage = "Error: Unable to fetch response. Please try again.";

      if (
        error.message.includes("401") ||
        error.message.includes("not authenticated")
      ) {
        errorMessage = "Authentication error. Please sign in again.";
        setTimeout(() => navigate("/signin"), 2000);
      } else if (error.message.includes("500")) {
        errorMessage = "Server error. Please try again later.";
      } else if (error.message.includes("Failed to fetch")) {
        errorMessage =
          "Connection error. Please check if the server is running.";
      }

      setMessages((prevMessages) => [
        ...prevMessages,
        {
          id: Date.now() + 1,
          content: errorMessage,
          sender: "bot",
        },
      ]);
    } finally {
      setIsLoading(false);
      setInputText("");
      setSelectedFiles([]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    const fileObjects = files.map((file) => ({
      name: file.name,
      type: file.type,
      url: URL.createObjectURL(file),
      size: file.size,
    }));

    setSelectedFiles([...selectedFiles, ...fileObjects]);
  };

  const removeFile = (index) => {
    const newFiles = [...selectedFiles];
    newFiles.splice(index, 1);
    setSelectedFiles(newFiles);
  };

  // Update the toggleRecording function
  const toggleRecording = async () => {
    if (!checkAuthentication()) {
      alert("Please sign in first to use voice recording.");
      navigate("/signin");
      return;
    }

    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
          },
        });

        const mediaRecorder = new MediaRecorder(stream, {
          mimeType: "audio/webm;codecs=opus",
        });

        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        mediaRecorder.onstop = async () => {
          try {
            const audioBlob = new Blob(audioChunksRef.current, {
              type: "audio/webm;codecs=opus",
            });

            const formData = new FormData();
            formData.append("file", audioBlob, "recording.webm");

            const response = await fetch(
              "http://localhost:8002/api/speech/record/",
              {
                method: "POST",
                credentials: "include", // Include cookies for authentication
                body: formData,
              }
            );

            if (!response.ok) {
              if (response.status === 401) {
                alert("Authentication failed. Please sign in again.");
                navigate("/signin");
                return;
              }
              throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (
              data.transcription &&
              data.transcription !== "No speech detected"
            ) {
              setInputText(data.transcription);
              // Note: Removed automatic send after transcription for better UX
              // User can review the transcription before sending
            } else {
              console.warn("No speech detected");
            }
          } catch (error) {
            console.error("Error processing audio:", error);
            alert("Failed to process speech. Please try again.");
          } finally {
            // Cleanup
            stream.getTracks().forEach((track) => track.stop());
          }
        };

        mediaRecorder.start();
        setIsRecording(true);

        // Stop recording after 5 seconds
        setTimeout(() => {
          if (mediaRecorderRef.current?.state === "recording") {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
          }
        }, 5000);
      } catch (error) {
        console.error("Microphone access error:", error);
        alert("Could not access microphone. Please check permissions.");
        setIsRecording(false);
      }
    } else {
      // Stop recording if already recording
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
    }
  };

  const goToHome = () => {
    navigate("/");
  };

  // Add effect to check authentication status on component mount
  useEffect(() => {
    const isAuth = checkAuthentication();
    if (!isAuth && window.location.pathname === "/chat") {
      console.log("No valid authentication found, redirecting to signin");
      // Optionally redirect to signin if on chat page without auth
      // navigate("/signin");
    }
  }, []);

  return (
    <div className="chat-interface">
      <Sidebar
        isOpen={isSidebarOpen}
        toggleSidebar={toggleSidebar}
        isLoggedIn={isLoggedIn}
        currentChat={{ messages }} // Pass current chat
      />
      <header className="chat-header">
        <div className="header-left">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="menu-button"
          >
            <Menu className="icon" />
          </Button>
          <h1 className="app-title">
            Dr.<span className="text-sky-500 font-bold"> MAMA</span>
          </h1>
          <Button
            variant="ghost"
            size="icon"
            onClick={goToHome}
            className="home-button"
          >
            <Home className="icon" />
          </Button>
        </div>

        <div className="header-right">
          {!isLoggedIn ? (
            <div className="auth-buttons">
              <Button
                variant="outline"
                onClick={() => navigate("/signin")}
                className="signin-button"
              >
                Sign In
              </Button>
              <Button
                onClick={() => navigate("/signup")}
                className="signup-button"
              >
                Sign Up
              </Button>
            </div>
          ) : (
            <div className="user-welcome">
              <span>Welcome back!</span>
            </div>
          )}
        </div>
      </header>

      <div className="messages-container">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {isLoading && (
          <div className="loading-message">
            <div className="bot-message">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        {selectedFiles.length > 0 && (
          <div className="file-previews">
            {selectedFiles.map((file, index) => (
              <div key={index} className="file-preview">
                {file.type.startsWith("image/") ? (
                  <div className="image-preview">
                    <img src={file.url || "/placeholder.svg"} alt={file.name} />
                  </div>
                ) : (
                  <div className="generic-preview">
                    <div className="file-icon"></div>
                  </div>
                )}
                <button
                  className="remove-file-button"
                  onClick={() => removeFile(index)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="text-input-container">
          <Textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Describe your symptoms or ask a medical question..."
            className="message-textarea"
            disabled={isLoading}
          />
          <div className="input-actions">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleRecording}
              className={`voice-button ${isRecording ? "recording" : ""}`}
              disabled={isLoading}
            >
              <Mic className={`icon ${isRecording ? "pulse" : ""}`} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => fileInputRef.current.click()}
              className="file-button"
              disabled={isLoading}
            >
              <PaperclipIcon className="icon" />
            </Button>
            <Button
              onClick={handleSendMessage}
              size="icon"
              className="send-button"
              disabled={
                isLoading || (!inputText.trim() && selectedFiles.length === 0)
              }
            >
              <Send className="icon" />
            </Button>
          </div>
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={handleFileSelect}
            multiple
            disabled={isLoading}
          />
        </div>
      </div>
    </div>
  );
}

// "use client";

// import { useState, useRef, useEffect } from "react";
// import { useNavigate, useLocation } from "react-router-dom";
// import { Button } from "./ui/button";
// import { Textarea } from "./ui/textarea";
// import { Menu, Send, PaperclipIcon, Home, Mic } from "lucide-react";
// import ChatMessage from "./chat-message";
// import Sidebar from "./sidebar";

// export default function ChatInterface({ toggleSidebar, isLoggedIn }) {
//   const [isSidebarOpen, setIsSidebarOpen] = useState(false);
//   const [messages, setMessages] = useState(() => {
//     // Check for passed state from history
//     const location = useLocation();
//     return (
//       location.state?.messages || [
//         {
//           id: 1,
//           content:
//             "Hello!! I'm Dr MAMA, your medical assistant. How can I help you?",
//           sender: "bot",
//         },
//       ]
//     );
//   });
//   const [inputText, setInputText] = useState("");
//   const [selectedFiles, setSelectedFiles] = useState([]);
//   const [isRecording, setIsRecording] = useState(false);

//   const navigate = useNavigate();
//   const fileInputRef = useRef(null);
//   const messagesEndRef = useRef(null);
//   const mediaRecorderRef = useRef(null);
//   const audioChunksRef = useRef([]);

//   // Scroll to bottom when messages change
//   useEffect(() => {
//     messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
//   }, [messages]);

//   const handleSendMessage = async () => {
//     if (!inputText.trim() && selectedFiles.length === 0) return;

//     const newMessage = {
//       id: Date.now(),
//       content: inputText,
//       sender: "user",
//       files: selectedFiles.length > 0 ? selectedFiles : undefined,
//     };

//     setMessages((prevMessages) => [...prevMessages, newMessage]);

//     try {
//       const userId = localStorage.getItem("user_id");

//       if (!userId) {
//         alert("Please sign in first to use the chatbot.");
//         navigate("/signin");
//         return;
//       }

//       const response = await fetch("http://localhost:8002/rag/query_rag/", {
//         method: "POST",
//         headers: {
//           "Content-Type": "application/json",
//         },
//         body: JSON.stringify({
//           user_id: parseInt(userId, 10), // ✅ Convert to integer
//           message: inputText,
//         }),
//       });

//       if (!response.ok) {
//         throw new Error(`HTTP error! status: ${response.status}`);
//       }

//       const data = await response.json();

//       const botResponse = {
//         id: Date.now() + 1,
//         content: data.response,
//         sender: "bot",
//       };

//       setMessages((prevMessages) => [...prevMessages, botResponse]);
//     } catch (error) {
//       console.error("Error:", error);
//       setMessages((prevMessages) => [
//         ...prevMessages,
//         {
//           id: Date.now() + 1,
//           content: "Error: Unable to fetch response. Please try again.",
//           sender: "bot",
//         },
//       ]);
//     }

//     setInputText("");
//     setSelectedFiles([]);
//   };

//   const handleKeyPress = (e) => {
//     if (e.key === "Enter" && !e.shiftKey) {
//       e.preventDefault();
//       handleSendMessage();
//     }
//   };

//   const handleFileSelect = (e) => {
//     const files = Array.from(e.target.files);
//     const fileObjects = files.map((file) => ({
//       name: file.name,
//       type: file.type,
//       url: URL.createObjectURL(file),
//       size: file.size,
//     }));

//     setSelectedFiles([...selectedFiles, ...fileObjects]);
//   };

//   const removeFile = (index) => {
//     const newFiles = [...selectedFiles];
//     newFiles.splice(index, 1);
//     setSelectedFiles(newFiles);
//   };

//   // Update the toggleRecording function
//   const toggleRecording = async () => {
//     if (!isRecording) {
//       try {
//         const stream = await navigator.mediaDevices.getUserMedia({
//           audio: {
//             channelCount: 1,
//             sampleRate: 16000,
//             echoCancellation: true,
//             noiseSuppression: true,
//           },
//         });

//         const mediaRecorder = new MediaRecorder(stream, {
//           mimeType: "audio/webm;codecs=opus",
//         });

//         mediaRecorderRef.current = mediaRecorder;
//         audioChunksRef.current = [];

//         mediaRecorder.ondataavailable = (event) => {
//           if (event.data.size > 0) {
//             audioChunksRef.current.push(event.data);
//           }
//         };

//         mediaRecorder.onstop = async () => {
//           try {
//             const audioBlob = new Blob(audioChunksRef.current, {
//               type: "audio/webm;codecs=opus",
//             });

//             const formData = new FormData();
//             formData.append("file", audioBlob, "recording.webm");

//             const response = await fetch(
//               "http://localhost:8002/api/speech/record/",
//               {
//                 method: "POST",
//                 body: formData,
//               }
//             );

//             if (!response.ok) {
//               throw new Error(`HTTP error! status: ${response.status}`);
//             }

//             const data = await response.json();

//             if (
//               data.transcription &&
//               data.transcription !== "No speech detected"
//             ) {
//               setInputText(data.transcription);
//               // Automatically send message after transcription
//               handleSendMessage();
//             } else {
//               console.warn("No speech detected");
//             }
//           } catch (error) {
//             console.error("Error processing audio:", error);
//             alert("Failed to process speech. Please try again.");
//           } finally {
//             // Cleanup
//             stream.getTracks().forEach((track) => track.stop());
//           }
//         };

//         mediaRecorder.start();
//         setIsRecording(true);

//         // Stop recording after 5 seconds
//         setTimeout(() => {
//           if (mediaRecorderRef.current?.state === "recording") {
//             mediaRecorderRef.current.stop();
//             setIsRecording(false);
//           }
//         }, 5000);
//       } catch (error) {
//         console.error("Microphone access error:", error);
//         alert("Could not access microphone. Please check permissions.");
//         setIsRecording(false);
//       }
//     } else {
//       // Stop recording if already recording
//       if (mediaRecorderRef.current?.state === "recording") {
//         mediaRecorderRef.current.stop();
//       }
//       setIsRecording(false);
//     }
//   };

//   const goToHome = () => {
//     navigate("/");
//   };

//   return (
//     <div className="chat-interface">
//       <Sidebar
//         isOpen={isSidebarOpen}
//         toggleSidebar={toggleSidebar}
//         isLoggedIn={isLoggedIn}
//         currentChat={{ messages }} // Pass current chat
//       />
//       <header className="chat-header">
//         <div className="header-left">
//           <Button
//             variant="ghost"
//             size="icon"
//             onClick={toggleSidebar}
//             className="menu-button"
//           >
//             <Menu className="icon" />
//           </Button>
//           <h1 className="app-title">
//             Dr.<span className="text-sky-500 font-bold"> MAMA</span>
//           </h1>
//           <Button
//             variant="ghost"
//             size="icon"
//             onClick={goToHome}
//             className="home-button"
//           >
//             <Home className="icon" />
//           </Button>
//         </div>

//         <div className="header-right">
//           {!isLoggedIn ? (
//             <div className="auth-buttons">
//               <Button
//                 variant="outline"
//                 onClick={() => navigate("/signin")}
//                 className="signin-button"
//               >
//                 Sign In
//               </Button>
//               <Button
//                 onClick={() => navigate("/signup")}
//                 className="signup-button"
//               >
//                 Sign Up
//               </Button>
//             </div>
//           ) : (
//             <div className="user-welcome">
//               <span>Welcome back!</span>
//             </div>
//           )}
//         </div>
//       </header>

//       <div className="messages-container">
//         {messages.map((message) => (
//           <ChatMessage key={message.id} message={message} />
//         ))}
//         <div ref={messagesEndRef} />
//       </div>

//       <div className="input-area">
//         {selectedFiles.length > 0 && (
//           <div className="file-previews">
//             {selectedFiles.map((file, index) => (
//               <div key={index} className="file-preview">
//                 {file.type.startsWith("image/") ? (
//                   <div className="image-preview">
//                     <img src={file.url || "/placeholder.svg"} alt={file.name} />
//                   </div>
//                 ) : (
//                   <div className="generic-preview">
//                     <div className="file-icon"></div>
//                   </div>
//                 )}
//                 <button
//                   className="remove-file-button"
//                   onClick={() => removeFile(index)}
//                 >
//                   ×
//                 </button>
//               </div>
//             ))}
//           </div>
//         )}

//         <div className="text-input-container">
//           <Textarea
//             value={inputText}
//             onChange={(e) => setInputText(e.target.value)}
//             onKeyDown={handleKeyPress}
//             placeholder="Describe your symptoms or ask a medical question..."
//             className="message-textarea"
//           />
//           <div className="input-actions">
//             <Button
//               variant="ghost"
//               size="icon"
//               onClick={toggleRecording}
//               className={`voice-button ${isRecording ? "recording" : ""}`}
//             >
//               <Mic className={`icon ${isRecording ? "pulse" : ""}`} />
//             </Button>
//             <Button
//               variant="ghost"
//               size="icon"
//               onClick={() => fileInputRef.current.click()}
//               className="file-button"
//             >
//               <PaperclipIcon className="icon" />
//             </Button>
//             <Button
//               onClick={handleSendMessage}
//               size="icon"
//               className="send-button"
//             >
//               <Send className="icon" />
//             </Button>
//           </div>
//           <input
//             type="file"
//             ref={fileInputRef}
//             className="hidden"
//             onChange={handleFileSelect}
//             multiple
//           />
//         </div>
//       </div>
//     </div>
//   );
// }
