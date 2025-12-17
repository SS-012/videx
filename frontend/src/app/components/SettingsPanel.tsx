"use client";

import { useState, useRef } from "react";
import { documentAPI } from "../services/api";

type SettingsPanelProps = {
	onBack?: () => void;
	onDocumentsRefresh?: () => void;
	labels?: string[];
	onLabelsChange?: (labels: string[]) => void;
};

const ALLOWED_EXTENSIONS = [".txt", ".json", ".csv", ".md", ".xml", ".html", ".htm"];

function isValidFile(file: File): boolean {
	const ext = "." + file.name.split(".").pop()?.toLowerCase();
	return ALLOWED_EXTENSIONS.includes(ext) && file.size > 0;
}

const DEFAULT_LABELS = ["ORG", "PERSON", "LOCATION", "DATE", "OTHER"];

export function SettingsPanel({ onBack, onDocumentsRefresh, labels: propLabels, onLabelsChange }: SettingsPanelProps) {
	const labels = propLabels || DEFAULT_LABELS;
	const [newLabel, setNewLabel] = useState("");
	const [isUploading, setIsUploading] = useState(false);
	const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });
	const fileInputRef = useRef<HTMLInputElement>(null);
	const folderInputRef = useRef<HTMLInputElement>(null);

	const addLabel = () => {
		if (newLabel.trim() && !labels.includes(newLabel.trim().toUpperCase())) {
			const newLabels = [...labels, newLabel.trim().toUpperCase()];
			if (onLabelsChange) {
				onLabelsChange(newLabels);
			}
			setNewLabel("");
		}
	};

	const removeLabel = (label: string) => {
		const newLabels = labels.filter((l) => l !== label);
		if (onLabelsChange) {
			onLabelsChange(newLabels);
		}
	};

	const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
		const uploadedFiles = event.target.files;
		if (!uploadedFiles || uploadedFiles.length === 0) return;

		const validFiles = Array.from(uploadedFiles).filter(isValidFile);
		if (validFiles.length === 0) {
			console.warn("No valid files to upload");
			event.target.value = "";
			return;
		}

		setIsUploading(true);
		setUploadProgress({ current: 0, total: validFiles.length });

		try {
			for (let i = 0; i < validFiles.length; i++) {
				await documentAPI.upload(validFiles[i]);
				setUploadProgress({ current: i + 1, total: validFiles.length });
			}
			if (onDocumentsRefresh) {
				onDocumentsRefresh();
			}
		} catch (error) {
			console.error("Failed to upload files:", error);
		} finally {
			setIsUploading(false);
			setUploadProgress({ current: 0, total: 0 });
			event.target.value = "";
		}
	};

	const triggerFileUpload = () => {
		fileInputRef.current?.click();
	};

	const triggerFolderUpload = () => {
		folderInputRef.current?.click();
	};

	return (
		<div className="h-full overflow-auto bg-black">
			<div className="mx-auto max-w-4xl px-8 py-8">
				{/* Header */}
				<div className="mb-8 border-b border-white/5 pb-6">
					<h2 className="text-2xl font-semibold text-white">Settings</h2>
					<p className="mt-1.5 text-sm text-slate-500">Configure your annotation environment</p>
				</div>

				<div className="space-y-8">
					{/* File Upload Section */}
					<div className="rounded-xl border border-white/10 bg-linear-to-br from-white/[0.03] to-white/[0.01] p-6 shadow-lg">
						<div className="mb-4">
							<h3 className="text-lg font-semibold text-white">Upload Documents</h3>
							<p className="mt-1.5 text-sm text-slate-400">Add files or entire folders to annotate</p>
						</div>

						{/* Hidden file inputs */}
						<input
							ref={fileInputRef}
							type="file"
							multiple
							accept=".txt,.json,.csv,.md,.xml,.html,.htm"
							className="hidden"
							onChange={handleFileUpload}
							disabled={isUploading}
						/>
						<input
							ref={folderInputRef}
							type="file"
							// @ts-expect-error - webkitdirectory is not in the types but works in browsers
							webkitdirectory=""
							multiple
							className="hidden"
							onChange={handleFileUpload}
							disabled={isUploading}
						/>

						{isUploading ? (
							<div className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-4 py-4">
								<div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-600 border-t-white"></div>
								<div className="flex-1">
									<p className="text-sm font-medium text-white">Uploading files...</p>
									<p className="mt-0.5 text-xs text-slate-400">
										{uploadProgress.current} of {uploadProgress.total} completed
									</p>
								</div>
								<div className="h-2 w-24 overflow-hidden rounded-full bg-white/5">
									<div
										className="h-full bg-white/20 transition-all duration-300"
										style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
									></div>
								</div>
							</div>
						) : (
							<div className="grid grid-cols-2 gap-3">
								<button
									onClick={triggerFileUpload}
									className="group flex cursor-pointer items-center justify-center gap-3 rounded-lg border border-white/10 bg-white/5 px-6 py-4 text-sm font-medium text-slate-300 transition-all hover:border-white/20 hover:bg-white/10 hover:text-white"
								>
									<svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											strokeWidth={1.5}
											d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
										/>
									</svg>
									<span>Upload Files</span>
								</button>
								<button
									onClick={triggerFolderUpload}
									className="group flex cursor-pointer items-center justify-center gap-3 rounded-lg border border-white/10 bg-white/5 px-6 py-4 text-sm font-medium text-slate-300 transition-all hover:border-white/20 hover:bg-white/10 hover:text-white"
								>
									<svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											strokeWidth={1.5}
											d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
										/>
									</svg>
									<span>Upload Folder</span>
								</button>
							</div>
						)}

						<div className="mt-4 rounded-lg bg-white/5 px-4 py-3">
							<p className="text-xs text-slate-500">
								<span className="font-medium text-slate-400">Supported formats:</span> .txt, .json, .csv, .md, .xml, .html, .htm
							</p>
						</div>
					</div>

					{/* Labels Configuration */}
					<div className="rounded-xl border border-white/10 bg-linear-to-br from-white/[0.03] to-white/[0.01] p-6 shadow-lg">
						<div className="mb-6">
							<h3 className="text-lg font-semibold text-white">Annotation Labels</h3>
							<p className="mt-1.5 text-sm text-slate-400">Configure the labels available for annotations</p>
						</div>

						{/* Existing Labels */}
						<div className="mb-6">
							<div className="mb-3">
								<span className="text-xs font-medium uppercase tracking-wider text-slate-500">Current Labels</span>
							</div>
							<div className="flex flex-wrap gap-4">
								{labels.map((label) => (
									<div
										key={label}
										className="flex items-center gap-2 rounded-lg text-sm font-medium"
										style={{
											border: "1px solid rgba(255,255,255,0.1)",
											backgroundColor: "rgba(255,255,255,0.05)",
											padding: "8px 14px",
											color: "#cbd5e1"
										}}
									>
										<span>{label}</span>
										<button
											onClick={() => removeLabel(label)}
											style={{
												cursor: "pointer",
												padding: "4px",
												borderRadius: "4px",
												color: "#ef4444",
												backgroundColor: "rgba(239,68,68,0.1)",
												border: "none",
												display: "flex",
												alignItems: "center",
												justifyContent: "center"
											}}
										>
											<svg style={{ width: "14px", height: "14px" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
											</svg>
										</button>
									</div>
								))}
							</div>
						</div>

						{/* Add New Label */}
						<div className="rounded-lg border border-white/10 bg-white/5 p-4">
							<label className="mb-2 block text-xs font-medium uppercase tracking-wider text-slate-400">Add New Label</label>
							<div className="flex gap-3">
								<input
									value={newLabel}
									onChange={(e) => setNewLabel(e.target.value)}
									onKeyDown={(e) => e.key === "Enter" && addLabel()}
									placeholder="Enter label name..."
									className="flex-1 rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-slate-600 transition-all focus:border-white/20 focus:bg-white/[0.07] focus:outline-none focus:ring-2 focus:ring-white/10"
								/>
								<button
									onClick={addLabel}
									className="cursor-pointer rounded-lg bg-white/10 px-6 py-2.5 text-sm font-semibold text-white transition-all hover:bg-white/20"
								>
									Add
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
