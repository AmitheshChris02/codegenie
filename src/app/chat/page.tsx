import ChatErrorBoundary from "@/components/chat/ChatErrorBoundary";
import ChatLayout from "@/components/chat/ChatLayout";

export default function ChatPage() {
  return (
    <ChatErrorBoundary>
      <ChatLayout />
    </ChatErrorBoundary>
  );
}
