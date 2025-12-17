"use client";

import { useState, useRef } from "react";
import { documentAPI } from "../services/api";

type DataFile = {
	id: string;
	name: string;
	content: string;
	status?: string;
};

type DataSidebarProps = {
	files: DataFile[];
	selectedFileId: string | null;
	onFileSelect: (fileId: string) => void;
	onSettingsClick: () => void;
	isSettingsView: boolean;
	onDocumentsRefresh?: () => void;
	onGoHome?: () => void;
	onFileUpload?: (files: FileList) => Promise<void>;
	onFileDelete?: (fileId: string) => Promise<void>;
};

const ALLOWED_EXTENSIONS = [".txt", ".json", ".csv", ".md", ".xml", ".html", ".htm"];

function isValidFile(file: File): boolean {
	const ext = "." + file.name.split(".").pop()?.toLowerCase();
	return ALLOWED_EXTENSIONS.includes(ext) && file.size > 0;
}

const MAX_VISIBLE_FILES = 10;
const FILE_ITEM_HEIGHT = 36; // Approximate height of each file item in pixels

export function DataSidebar({
	files,
	selectedFileId,
	onFileSelect,
	onSettingsClick,
	isSettingsView,
	onDocumentsRefresh,
	onGoHome,
	onFileUpload,
	onFileDelete,
}: DataSidebarProps) {
	const [isDataExpanded, setIsDataExpanded] = useState(true);
	const [isSettingsExpanded, setIsSettingsExpanded] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);
	const folderInputRef = useRef<HTMLInputElement>(null);

	const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
		const uploadedFiles = event.target.files;
		if (!uploadedFiles || uploadedFiles.length === 0) return;

		const validFiles = Array.from(uploadedFiles).filter(isValidFile);
		if (validFiles.length === 0) {
			console.warn("No valid files to upload");
			event.target.value = "";
			return;
		}

		if (onFileUpload) {
			await onFileUpload(uploadedFiles);
		} else {
			try {
				for (const file of validFiles) {
					await documentAPI.upload(file);
				}
				if (onDocumentsRefresh) {
					onDocumentsRefresh();
				}
			} catch (error) {
				console.error("Failed to upload files:", error);
			}
		}
		event.target.value = "";
	};

	const triggerFileUpload = () => {
		fileInputRef.current?.click();
	};

	const triggerFolderUpload = () => {
		folderInputRef.current?.click();
	};

	const visibleFiles = files.slice(0, MAX_VISIBLE_FILES);
	const hasMoreFiles = files.length > MAX_VISIBLE_FILES;
	const dataSectionMaxHeight = `${Math.min(visibleFiles.length, MAX_VISIBLE_FILES) * FILE_ITEM_HEIGHT + 20}px`;

	return (
		<aside className="flex h-full flex-col bg-[#0a0a0a]">
			{/* Header */}
			<div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
				<button
					onClick={onGoHome}
					className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-white/5"
				>
					<span className="text-base font-semibold text-white">Videx</span>
				</button>
			</div>

			{/* Navigation */}
			<nav className="flex flex-1 flex-col overflow-hidden">
				{/* Data Section */}
				<div className="flex flex-col border-b border-white/5">
					<button
						onClick={() => setIsDataExpanded(!isDataExpanded)}
						className="flex cursor-pointer items-center gap-2 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-300"
					>
						<svg
							className={`h-3.5 w-3.5 transition-transform duration-200 ${isDataExpanded ? "rotate-90" : ""}`}
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
						</svg>
						<span>Data</span>
						<span className="ml-auto rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-medium text-slate-500">
							{files.length}
						</span>
					</button>

					{isDataExpanded && (
						<div
							className="overflow-y-auto px-2 py-1"
							style={{ maxHeight: hasMoreFiles ? dataSectionMaxHeight : "none" }}
						>
							{files.length === 0 ? (
								<div className="px-3 py-8 text-center">
									<div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-white/5">
										<svg className="h-4 w-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												strokeLinecap="round"
												strokeLinejoin="round"
												strokeWidth={1.5}
												d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
											/>
										</svg>
									</div>
									<p className="text-xs text-slate-600">No files yet</p>
									<p className="mt-1 text-[10px] text-slate-700">Upload files in Settings</p>
								</div>
							) : (
								<div className="space-y-0.5">
									{files.map((file) => (
										<div
											key={file.id}
											className={`group relative flex w-full items-center rounded-md py-2 pr-2 text-left text-sm transition-all ${
												selectedFileId === file.id && !isSettingsView
													? "text-white"
													: "text-slate-400 hover:bg-white/5 hover:text-slate-200"
											}`}
											style={
												selectedFileId === file.id && !isSettingsView
													? { 
														backgroundColor: "rgba(59, 130, 246, 0.2)", 
														boxShadow: "inset 0 0 0 1px rgba(59, 130, 246, 0.4)",
														paddingLeft: "1.75rem"
													}
													: { paddingLeft: "1rem" }
											}
										>
											<button
												onClick={() => onFileSelect(file.id)}
												className="flex min-w-0 flex-1 cursor-pointer items-center gap-2"
											>
												<svg
													className="h-3.5 w-3.5 shrink-0 opacity-50"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														strokeLinecap="round"
														strokeLinejoin="round"
														strokeWidth={1.5}
														d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
													/>
												</svg>
												<span className="truncate text-[13px]">{file.name}</span>
											</button>
											{onFileDelete && (
												<button
													onClick={(e) => {
														e.stopPropagation();
														onFileDelete(file.id);
													}}
													style={{
														display: "flex",
														alignItems: "center",
														justifyContent: "center",
														width: "24px",
														height: "24px",
														borderRadius: "4px",
														flexShrink: 0,
														color: "#64748b",
														cursor: "pointer",
														backgroundColor: "transparent",
														border: "none",
													}}
													onMouseEnter={(e) => {
														e.currentTarget.style.backgroundColor = "rgba(239,68,68,0.2)";
														e.currentTarget.style.color = "#f87171";
													}}
													onMouseLeave={(e) => {
														e.currentTarget.style.backgroundColor = "transparent";
														e.currentTarget.style.color = "#64748b";
													}}
													title="Delete file"
												>
													<svg
														style={{ width: "14px", height: "14px" }}
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															strokeLinecap="round"
															strokeLinejoin="round"
															strokeWidth={2}
															d="M6 18L18 6M6 6l12 12"
														/>
													</svg>
												</button>
											)}
										</div>
									))}
								</div>
							)}
						</div>
					)}
				</div>

				{/* Settings Section - Below Data, slides down dynamically */}
				<div className="flex flex-col">
					<button
						onClick={() => setIsSettingsExpanded(!isSettingsExpanded)}
						className="flex cursor-pointer items-center gap-2 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-300"
					>
						<svg
							className={`h-3.5 w-3.5 transition-transform duration-200 ${isSettingsExpanded ? "rotate-90" : ""}`}
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
						</svg>
						<span>Settings</span>
					</button>

					{isSettingsExpanded && (
						<div className="px-2 py-2">
							<button
								onClick={onSettingsClick}
								className={`flex w-full cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm transition-all ${
									isSettingsView
										? "bg-white/10 text-white"
										: "text-slate-400 hover:bg-white/5 hover:text-slate-200"
								}`}
								style={{ paddingLeft: "1.5rem" }}
							>
								<svg className="h-3.5 w-3.5 shrink-0 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										strokeLinecap="round"
										strokeLinejoin="round"
										strokeWidth={1.5}
										d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
									/>
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
								</svg>
								<span className="text-[13px]">Open Settings</span>
							</button>
						</div>
					)}
				</div>
			</nav>

			{/* Hidden file inputs - moved to SettingsPanel */}
			<input ref={fileInputRef} type="file" multiple accept=".txt,.json,.csv,.md,.xml,.html,.htm" className="hidden" onChange={handleFileUpload} />
			<input
				ref={folderInputRef}
				type="file"
				// @ts-expect-error - webkitdirectory is not in the types but works in browsers
				webkitdirectory=""
				multiple
				className="hidden"
				onChange={handleFileUpload}
			/>
		</aside>
	);
}
