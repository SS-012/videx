"use client";

import { useState, useRef, useEffect } from "react";

type Message = {
	id: string;
	role: "user" | "assistant";
	content: string;
	toolResults?: ToolResult[];
	suggestions?: Suggestion[];
	annotationsCreated?: AnnotationResult[];
};

type ToolResult = {
	tool: string;
	args: Record<string, unknown>;
	result: Record<string, unknown>;
};

type Suggestion = {
	text?: string;
	label: string;
	confidence: number;
};

type AnnotationResult = {
	id?: string;
	text: string;
	label: string;
	span_start?: number;
	span_end?: number;
};

type ChatPanelProps = {
	documentId?: string;
	documentContent?: string;
	onAnnotationCreated?: () => void;
	onSuggestionAccept?: (suggestion: Suggestion) => void;
	labels?: string[];
	messages?: Message[];
	onMessagesChange?: (messages: Message[]) => void;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const LABEL_COLORS: Record<string, { bg: string; text: string }> = {
	ORG: { bg: "bg-blue-500/20", text: "text-blue-400" },
	PERSON: { bg: "bg-green-500/20", text: "text-green-400" },
	LOCATION: { bg: "bg-purple-500/20", text: "text-purple-400" },
	DATE: { bg: "bg-orange-500/20", text: "text-orange-400" },
	OTHER: { bg: "bg-slate-500/20", text: "text-slate-400" },
};

export function ChatPanel({ documentId, documentContent, onAnnotationCreated, onSuggestionAccept, labels, messages: propMessages, onMessagesChange }: ChatPanelProps) {
	const messages = propMessages || [];
	const messagesRef = useRef(messages);
	
	useEffect(() => {
		messagesRef.current = messages;
	}, [messages]);
	
	const setMessages = (newMessages: Message[] | ((prev: Message[]) => Message[])) => {
		if (onMessagesChange) {
			if (typeof newMessages === "function") {
				const updated = newMessages(messagesRef.current);
				messagesRef.current = updated;
				onMessagesChange(updated);
			} else {
				messagesRef.current = newMessages;
				onMessagesChange(newMessages);
			}
		}
	};
	
	const [input, setInput] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const messagesEndRef = useRef<HTMLDivElement>(null);

	const scrollToBottom = () => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
	};

	useEffect(() => {
		scrollToBottom();
	}, [messages]);

	const handleSend = async () => {
		if (!input.trim() || isLoading) return;

		const userMessage: Message = {
			id: Date.now().toString(),
			role: "user",
			content: input,
		};

		setMessages((prev) => [...prev, userMessage]);
		setInput("");
		setIsLoading(true);

		try {
			const response = await fetch(`${API_BASE_URL}/chat`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					message: input,
					document_id: documentId,
					document_context: documentContent,
					labels: labels,
					history: messages.slice(-6).map((m) => ({
						role: m.role,
						content: m.content,
					})),
				}),
			});

			if (response.ok) {
				const data = await response.json();
				
				const assistantMessage: Message = {
					id: (Date.now() + 1).toString(),
					role: "assistant",
					content: data.response || "I couldn't generate a response.",
					toolResults: data.tool_results,
					suggestions: data.suggestions,
					annotationsCreated: data.annotations_created,
				};
				
				setMessages((prev) => [...prev, assistantMessage]);

				if (data.annotations_created?.length > 0 && onAnnotationCreated) {
					onAnnotationCreated();
				}
			} else {
				const fallbackMessage: Message = {
					id: (Date.now() + 1).toString(),
					role: "assistant",
					content: "I'm having trouble connecting. Make sure the backend is running.",
				};
				setMessages((prev) => [...prev, fallbackMessage]);
			}
		} catch (error) {
			console.error("Chat error:", error);
			const errorMessage: Message = {
				id: (Date.now() + 1).toString(),
				role: "assistant",
				content: "Unable to connect to the chat service. Make sure the backend is running.",
			};
			setMessages((prev) => [...prev, errorMessage]);
		} finally {
			setIsLoading(false);
		}
	};

	const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			handleSend();
		}
	};

	const handleAcceptSuggestion = async (suggestion: Suggestion) => {
		if (!documentId || !documentContent || !suggestion.text) return;

		const startIdx = documentContent.indexOf(suggestion.text);
		if (startIdx === -1) return;

		try {
			const response = await fetch(`${API_BASE_URL}/annotations/documents/${documentId}`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					label: suggestion.label,
					span_start: startIdx,
					span_end: startIdx + suggestion.text.length,
					text: suggestion.text,
					confidence: suggestion.confidence,
					source: "ai",
				}),
			});

			if (response.ok) {
				setMessages((prev) =>
					prev.map((msg) => ({
						...msg,
						suggestions: msg.suggestions?.filter((s) => s !== suggestion),
					}))
				);

				if (onAnnotationCreated) {
					onAnnotationCreated();
				}
			}
		} catch (error) {
			console.error("Failed to accept suggestion:", error);
		}
	};

	const suggestedPrompts = documentId
		? [
				"Scan this document",
				"What have I tagged so far?",
				"Any entities I missed?",
		  ]
		: [
				"What can you do?",
				"Available labels?",
				"How does this work?",
		  ];

	const renderMessageContent = (message: Message) => {
		return (
			<div>
				{/* Main response text */}
				<p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>

				{/* Show created annotations */}
				{message.annotationsCreated && message.annotationsCreated.length > 0 && (
					<div className="mt-3 rounded-lg border border-green-500/20 bg-green-500/10 p-2">
						<p className="mb-2 text-xs font-medium text-green-400">✓ Created Annotations:</p>
						<div className="flex flex-wrap gap-1">
							{message.annotationsCreated.map((ann, idx) => {
								const colors = LABEL_COLORS[ann.label] || LABEL_COLORS.OTHER;
								return (
									<span
										key={idx}
										className={`rounded px-1.5 py-0.5 text-xs ${colors.bg} ${colors.text}`}
									>
										{ann.label}: &quot;{ann.text}&quot;
									</span>
								);
							})}
						</div>
					</div>
				)}

				{/* Show suggestions with accept buttons */}
				{message.suggestions && message.suggestions.length > 0 && (
					<div className="mt-3 space-y-2">
						<p className="text-xs font-medium text-slate-500">Suggestions:</p>
						{message.suggestions.map((suggestion, idx) => {
							const colors = LABEL_COLORS[suggestion.label] || LABEL_COLORS.OTHER;
							return (
								<div
									key={idx}
									className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] p-2"
								>
									<div className="flex items-center gap-2 overflow-hidden">
										<span className={`shrink-0 rounded px-1.5 py-0.5 text-xs ${colors.bg} ${colors.text}`}>
											{suggestion.label}
										</span>
										<span className="truncate text-xs text-slate-400">&quot;{suggestion.text}&quot;</span>
									</div>
									<button
										onClick={() => handleAcceptSuggestion(suggestion)}
										className="shrink-0 cursor-pointer rounded bg-green-500/10 px-2 py-1 text-xs text-green-400 transition-colors hover:bg-green-500/20"
									>
										Accept
									</button>
								</div>
							);
						})}
					</div>
				)}
			</div>
		);
	};

	return (
		<div className="flex h-full flex-col bg-[#0a0a0a]">
			{/* Header */}
			<div className="border-b border-white/5 px-4 py-3">
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-2">
						<div className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-500">
							<svg className="h-3.5 w-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
						</div>
						<h3 className="text-sm font-medium text-white">VIDEX</h3>
					</div>
					{messages.length > 0 && (
						<button
							onClick={() => setMessages([])}
							className="cursor-pointer rounded px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
							title="Clear chat history"
						>
							Clear
						</button>
					)}
				</div>
				{documentId && (
					<p className="mt-1 text-xs text-slate-500">Working on current document</p>
				)}
			</div>

			{/* Messages area */}
			<div className="flex-1 overflow-y-auto px-4 py-4">
				{messages.length === 0 ? (
					<div className="flex h-full flex-col items-center justify-center px-4">
						<div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20">
							<svg className="h-6 w-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={1.5}
									d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
								/>
							</svg>
						</div>
						<p className="mb-1 text-center text-sm font-medium text-slate-300">VIDEX Online</p>
						<p className="mb-4 text-center text-xs text-slate-500">
							{documentId ? "Document loaded. Ready to analyze." : "Awaiting document selection."}
						</p>
						<div className="w-full space-y-2">
							{suggestedPrompts.map((prompt, idx) => (
								<button
									key={idx}
									onClick={() => setInput(prompt)}
									className="block w-full cursor-pointer rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2.5 text-left text-xs text-slate-400 transition-all hover:border-white/10 hover:bg-white/5 hover:text-slate-300"
								>
									{prompt}
								</button>
							))}
						</div>
					</div>
				) : (
					<div className="space-y-4">
						{messages.map((message) => (
							<div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
								<div
									className={`max-w-[90%] rounded-2xl px-4 py-2.5 text-sm ${
										message.role === "user"
											? "bg-blue-500/20 text-white"
											: "bg-white/5 text-slate-300"
									}`}
								>
									{message.role === "assistant" ? renderMessageContent(message) : (
										<p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
									)}
								</div>
							</div>
						))}
						{isLoading && (
							<div className="flex justify-start">
								<div className="rounded-2xl bg-white/5 px-4 py-3">
									<div className="flex items-center gap-2">
										<div className="flex gap-1">
											<div className="h-2 w-2 animate-bounce rounded-full bg-blue-400 [animation-delay:-0.3s]"></div>
											<div className="h-2 w-2 animate-bounce rounded-full bg-blue-400 [animation-delay:-0.15s]"></div>
											<div className="h-2 w-2 animate-bounce rounded-full bg-blue-400"></div>
										</div>
										<span className="text-xs text-slate-500">Thinking...</span>
									</div>
								</div>
							</div>
						)}
						<div ref={messagesEndRef} />
					</div>
				)}
			</div>

			{/* Input area */}
			<div className="border-t border-white/5 p-3">
				<div className="relative">
					<textarea
						value={input}
						onChange={(e) => setInput(e.target.value)}
						onKeyDown={handleKeyDown}
						placeholder={documentId ? "Ask me to find entities, create annotations..." : "Ask about annotation..."}
						rows={1}
						disabled={isLoading}
						className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-4 py-3 pr-12 text-sm text-white placeholder-slate-500 transition-all focus:border-blue-500/50 focus:bg-white/[0.07] focus:outline-none disabled:opacity-50"
					/>
					<button
						onClick={handleSend}
						disabled={!input.trim() || isLoading}
						className="absolute bottom-2 right-2 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg bg-blue-500 text-white transition-all hover:bg-blue-400 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-slate-500"
					>
						<svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
						</svg>
					</button>
				</div>
			</div>
		</div>
	);
}
