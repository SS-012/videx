"use client";

import { useState, useEffect, useCallback } from "react";
import { DataSidebar } from "./components/DataSidebar";
import { TextViewer } from "./components/TextViewer";
import { ChatPanel } from "./components/ChatPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { documentAPI } from "./services/api";

type ViewMode = "text" | "settings";

type DataFile = {
	id: string;
	name: string;
	content: string;
	status?: string;
};

const DEFAULT_LABELS = ["ORG", "PERSON", "LOCATION", "DATE", "OTHER"];

export default function HomePage() {
	const [dataFiles, setDataFiles] = useState<DataFile[]>([]);
	const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
	const [viewMode, setViewMode] = useState<ViewMode>("text");
	const [loading, setLoading] = useState(false);
	const [annotationRefreshKey, setAnnotationRefreshKey] = useState(0);
	const [labels, setLabels] = useState<string[]>(DEFAULT_LABELS);
	const [chatMessages, setChatMessages] = useState<Array<{id: string; role: "user" | "assistant"; content: string; toolResults?: unknown[]; suggestions?: unknown[]; annotationsCreated?: unknown[]}>>([]);

	useEffect(() => {
		const savedLabels = localStorage.getItem("videx-labels");
		if (savedLabels) {
			try {
				setLabels(JSON.parse(savedLabels));
			} catch (e) {
				console.error("Failed to parse saved labels:", e);
			}
		}
		
		const savedMessages = localStorage.getItem("videx-chat-messages");
		if (savedMessages) {
			try {
				setChatMessages(JSON.parse(savedMessages));
			} catch (e) {
				console.error("Failed to parse saved messages:", e);
			}
		}
	}, []);

	useEffect(() => {
		localStorage.setItem("videx-labels", JSON.stringify(labels));
	}, [labels]);

	useEffect(() => {
		localStorage.setItem("videx-chat-messages", JSON.stringify(chatMessages));
	}, [chatMessages]);

	useEffect(() => {
		loadDocuments();
	}, []);

	const loadDocuments = async () => {
		setLoading(true);
		try {
			const docs = await documentAPI.list();
			const files: DataFile[] = docs.map((doc) => ({
				id: doc.id,
				name: doc.title,
				content: doc.content || "",
				status: doc.status,
			}));
			setDataFiles(files);
		} catch (error) {
			console.error("Failed to load documents:", error);
		} finally {
			setLoading(false);
		}
	};

	const handleFileSelect = useCallback(async (fileId: string) => {
		setSelectedFileId(fileId);
		setViewMode("text");

		const file = dataFiles.find((f) => f.id === fileId);
		if (file && !file.content) {
			try {
				const contentData = await documentAPI.getContent(fileId);
				if (contentData.content) {
					setDataFiles((files) =>
						files.map((f) => (f.id === fileId ? { ...f, content: contentData.content } : f))
					);
				}
			} catch (error) {
				console.error("Failed to load document content:", error);
			}
		}
	}, [dataFiles]);

	const handleSettingsClick = () => {
		setViewMode("settings");
	};

	const handleGoHome = () => {
		setViewMode("text");
		setSelectedFileId(null);
	};

	const handleFileDelete = async (fileId: string) => {
		try {
			await documentAPI.delete(fileId);
			if (selectedFileId === fileId) {
				setSelectedFileId(null);
			}
			loadDocuments();
		} catch (error) {
			console.error("Failed to delete document:", error);
		}
	};

	const handleNavigate = useCallback((direction: "prev" | "next") => {
		if (!selectedFileId) return;

		const currentIndex = dataFiles.findIndex((f) => f.id === selectedFileId);
		if (currentIndex === -1) return;

		let newIndex: number;
		if (direction === "prev") {
			newIndex = currentIndex > 0 ? currentIndex - 1 : currentIndex;
		} else {
			newIndex = currentIndex < dataFiles.length - 1 ? currentIndex + 1 : currentIndex;
		}

		handleFileSelect(dataFiles[newIndex].id);
	}, [selectedFileId, dataFiles, handleFileSelect]);

	const selectedFile = dataFiles.find((f) => f.id === selectedFileId) || null;
	const currentIndex = selectedFileId ? dataFiles.findIndex((f) => f.id === selectedFileId) : -1;
	const canNavigatePrev = currentIndex > 0;
	const canNavigateNext = currentIndex >= 0 && currentIndex < dataFiles.length - 1;

	return (
		<div className="flex h-screen w-full bg-black">
			{/* Left Sidebar */}
			<div className="w-[260px] shrink-0 border-r border-white/5">
				<DataSidebar
					files={dataFiles}
					selectedFileId={selectedFileId}
					onFileSelect={handleFileSelect}
					onSettingsClick={handleSettingsClick}
					isSettingsView={viewMode === "settings"}
					onDocumentsRefresh={loadDocuments}
					onGoHome={handleGoHome}
					onFileDelete={handleFileDelete}
				/>
			</div>

			{/* Main Content Area */}
			<div className="flex-1 border-r border-white/5">
				{viewMode === "text" ? (
					<TextViewer
						file={selectedFile}
						onNavigate={handleNavigate}
						canNavigatePrev={canNavigatePrev}
						canNavigateNext={canNavigateNext}
						refreshKey={annotationRefreshKey}
						labels={labels}
					/>
				) : (
					<SettingsPanel 
						onBack={() => setViewMode("text")} 
						onDocumentsRefresh={loadDocuments}
						labels={labels}
						onLabelsChange={setLabels}
					/>
				)}
			</div>

			{/* Right Chat Panel */}
			<div className="w-[340px] shrink-0">
				<ChatPanel
					documentId={selectedFileId || undefined}
					documentContent={selectedFile?.content}
					onAnnotationCreated={() => setAnnotationRefreshKey((k) => k + 1)}
					labels={labels}
					messages={chatMessages}
					onMessagesChange={setChatMessages}
				/>
			</div>
		</div>
	);
}
