"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { annotationAPI, type Annotation, type Suggestion } from "../services/api";

type DataFile = {
	id: string;
	name: string;
	content: string;
};

type TextViewerProps = {
	file: DataFile | null;
	onNavigate: (direction: "prev" | "next") => void;
	canNavigatePrev: boolean;
	canNavigateNext: boolean;
	refreshKey?: number;
	labels?: string[];
};

const DEFAULT_LABELS = ["ORG", "PERSON", "LOCATION", "DATE", "OTHER"];

const LABEL_COLORS: Record<string, { bg: string; border: string; text: string }> = {
	ORG: { bg: "bg-blue-500/20", border: "border-blue-500/50", text: "text-blue-400" },
	PERSON: { bg: "bg-green-500/20", border: "border-green-500/50", text: "text-green-400" },
	LOCATION: { bg: "bg-purple-500/20", border: "border-purple-500/50", text: "text-purple-400" },
	DATE: { bg: "bg-orange-500/20", border: "border-orange-500/50", text: "text-orange-400" },
	OTHER: { bg: "bg-slate-500/20", border: "border-slate-500/50", text: "text-slate-400" },
};

type Selection = {
	text: string;
	start: number;
	end: number;
};

export function TextViewer({ file, onNavigate, canNavigatePrev, canNavigateNext, refreshKey, labels: propLabels }: TextViewerProps) {
	const labels = propLabels || DEFAULT_LABELS;
	const [annotations, setAnnotations] = useState<Annotation[]>([]);
	const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
	const [selection, setSelection] = useState<Selection | null>(null);
	const [showLabelsDropdown, setShowLabelsDropdown] = useState(false);
	const [loading, setLoading] = useState(false);
	const [loadingSuggestions, setLoadingSuggestions] = useState(false);
	const contentRef = useRef<HTMLDivElement>(null);
	const labelsDropdownRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (file) {
			loadAnnotations();
			setSuggestions([]);
			setSelection(null);
			setShowLabelsDropdown(false);
		}
	}, [file?.id]);

	useEffect(() => {
		if (file && refreshKey) {
			loadAnnotations();
		}
	}, [refreshKey]);

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === "ArrowLeft" && canNavigatePrev) {
				onNavigate("prev");
			} else if (e.key === "ArrowRight" && canNavigateNext) {
				onNavigate("next");
			} else if (e.key === "Escape") {
				setSelection(null);
				setShowLabelsDropdown(false);
				window.getSelection()?.removeAllRanges();
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [onNavigate, canNavigatePrev, canNavigateNext]);

	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (labelsDropdownRef.current && !labelsDropdownRef.current.contains(event.target as Node)) {
				setShowLabelsDropdown(false);
			}
		};

		if (showLabelsDropdown) {
			document.addEventListener("mousedown", handleClickOutside);
			return () => document.removeEventListener("mousedown", handleClickOutside);
		}
	}, [showLabelsDropdown]);

	const loadAnnotations = async () => {
		if (!file) return;
		try {
			const anns = await annotationAPI.listByDocument(file.id);
			setAnnotations(anns);
		} catch (error) {
			console.error("Failed to load annotations:", error);
		}
	};

	const handleTextSelection = useCallback(() => {
		const windowSelection = window.getSelection();
		if (!windowSelection || windowSelection.isCollapsed || !contentRef.current) {
			setSelection(null);
			return;
		}

		const selectedText = windowSelection.toString().trim();
		if (!selectedText) {
			setSelection(null);
			return;
		}

		const textContent = file?.content || "";
		const range = windowSelection.getRangeAt(0);
		
		const preCaretRange = range.cloneRange();
		preCaretRange.selectNodeContents(contentRef.current);
		preCaretRange.setEnd(range.startContainer, range.startOffset);
		const startIndex = preCaretRange.toString().length;
		const endIndex = startIndex + selectedText.length;

		setSelection({
			text: selectedText,
			start: startIndex,
			end: endIndex,
		});
	}, [file?.content]);

	const handleLabelSelect = async (label: string) => {
		if (!selection || !file) return;

		setLoading(true);
		setShowLabelsDropdown(false);
		try {
			await annotationAPI.create(file.id, {
				label,
				span_start: selection.start,
				span_end: selection.end,
				text: selection.text,
				confidence: 1.0,
				source: "manual",
			});

			await loadAnnotations();
			setSelection(null);
			window.getSelection()?.removeAllRanges();
		} catch (error) {
			console.error("Failed to create annotation:", error);
		} finally {
			setLoading(false);
		}
	};

	const handleGetSuggestions = async () => {
		if (!file) return;

		setLoadingSuggestions(true);
		try {
			const result = await annotationAPI.suggest(file.id, {
				task: "ner",
				labels: labels,
				top_k: 5,
			});
			setSuggestions(result.suggestions);
		} catch (error) {
			console.error("Failed to get suggestions:", error);
			setSuggestions([]);
		} finally {
			setLoadingSuggestions(false);
		}
	};

	const handleAcceptSuggestion = async (suggestion: Suggestion) => {
		if (!file) return;

		setLoading(true);
		try {
			await annotationAPI.create(file.id, {
				label: suggestion.label,
				span_start: suggestion.span_start || 0,
				span_end: suggestion.span_end || 0,
				text: suggestion.text,
				confidence: suggestion.confidence,
				source: "ai",
			});

			await loadAnnotations();
			setSuggestions(suggestions.filter((s) => s !== suggestion));
		} catch (error) {
			console.error("Failed to accept suggestion:", error);
		} finally {
			setLoading(false);
		}
	};

	const handleDeleteAnnotation = async (annotation: Annotation) => {
		if (!file) return;

		try {
			await annotationAPI.delete(file.id, annotation.id);
			await loadAnnotations();
		} catch (error) {
			console.error("Failed to delete annotation:", error);
		}
	};

	const handleAcceptAnnotation = async (annotation: Annotation) => {
		if (!file) return;

		try {
			await annotationAPI.accept(file.id, annotation.id);
			await loadAnnotations();
		} catch (error) {
			console.error("Failed to accept annotation:", error);
		}
	};

	const handleRejectAnnotation = async (annotation: Annotation) => {
		if (!file) return;

		try {
			await annotationAPI.reject(file.id, annotation.id);
			await loadAnnotations();
		} catch (error) {
			console.error("Failed to reject annotation:", error);
		}
	};

	const handleAcceptAllPending = async () => {
		if (!file) return;
		const pending = annotations.filter(a => a.source === "pending_batch");
		for (const ann of pending) {
			try {
				await annotationAPI.accept(file.id, ann.id);
			} catch (error) {
				console.error("Failed to accept annotation:", error);
			}
		}
		await loadAnnotations();
	};

	const handleRejectAllPending = async () => {
		if (!file) return;
		const pending = annotations.filter(a => a.source === "pending_batch");
		for (const ann of pending) {
			try {
				await annotationAPI.reject(file.id, ann.id);
			} catch (error) {
				console.error("Failed to reject annotation:", error);
			}
		}
		await loadAnnotations();
	};

	const renderHighlightedContent = () => {
		if (!file) return null;

		const content = file.content;
		const allAnnotations = [...annotations].sort((a, b) => a.span_start - b.span_start);

		if (allAnnotations.length === 0) {
			return content;
		}

		const parts: React.ReactNode[] = [];
		let lastIndex = 0;

		allAnnotations.forEach((ann, idx) => {
			if (ann.span_start > lastIndex) {
				parts.push(content.slice(lastIndex, ann.span_start));
			}

			const colors = LABEL_COLORS[ann.label] || LABEL_COLORS.OTHER;
			const isPending = ann.source === "pending_batch";
			
			parts.push(
				<span
					key={`ann-${idx}`}
					className={isPending 
						? "cursor-pointer border-b-2 transition-all hover:opacity-80" 
						: `${colors.bg} ${colors.border} cursor-pointer border-b-2 transition-all hover:opacity-80`
					}
					style={isPending ? {
						backgroundColor: "rgba(234,179,8,0.2)",
						borderBottomColor: "rgba(234,179,8,0.8)",
						borderBottomWidth: "2px",
						borderBottomStyle: "dashed"
					} : undefined}
					title={isPending ? `${ann.label} (PENDING - click to review)` : `${ann.label} (${ann.source})`}
				>
					{content.slice(ann.span_start, ann.span_end)}
				</span>
			);

			lastIndex = ann.span_end;
		});

		if (lastIndex < content.length) {
			parts.push(content.slice(lastIndex));
		}

		return parts;
	};

	if (!file) {
		return (
			<div className="flex h-full items-center justify-center bg-black">
				<div className="text-center">
					<div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white/5">
						<svg className="h-8 w-8 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								strokeWidth={1.5}
								d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
							/>
						</svg>
					</div>
					<h3 className="text-base font-medium text-slate-400">No file selected</h3>
					<p className="mt-1 text-sm text-slate-600">Choose a file from the sidebar</p>
				</div>
			</div>
		);
	}

	return (
		<div className="flex h-full flex-col bg-black">
			{/* Toolbar */}
			<div 
				className="flex flex-col bg-[#0a0a0a]"
				style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
			>
				{/* First Row: Navigation and File Name */}
				<div className="flex items-center" style={{ padding: "10px 16px" }}>
					{/* Navigation */}
					<div className="flex items-center" style={{ gap: "12px" }}>
						<button
							onClick={() => onNavigate("prev")}
							disabled={!canNavigatePrev}
							className="flex items-center justify-center rounded-md cursor-pointer"
							style={{ 
								width: "32px", 
								height: "32px", 
								color: "#64748b",
								opacity: canNavigatePrev ? 1 : 0.3,
							}}
						>
							<svg style={{ width: "16px", height: "16px" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
							</svg>
						</button>
						<button
							onClick={() => onNavigate("next")}
							disabled={!canNavigateNext}
							className="flex items-center justify-center rounded-md cursor-pointer"
							style={{ 
								width: "32px", 
								height: "32px", 
								color: "#64748b",
								opacity: canNavigateNext ? 1 : 0.3,
							}}
						>
							<svg style={{ width: "16px", height: "16px" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
							</svg>
						</button>
					</div>

					{/* Separator */}
					<div style={{ margin: "0 24px", width: "1px", height: "24px", backgroundColor: "rgba(255,255,255,0.1)" }}></div>

					{/* File Name */}
					<span className="flex-1 truncate text-sm font-medium" style={{ color: "#cbd5e1" }}>{file.name}</span>
				</div>

				{/* Second Row: Labels and AI Suggest */}
				<div className="flex items-center px-4 py-2" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
					{/* Labels Dropdown */}
					<div className="relative" style={{ marginRight: "24px" }} ref={labelsDropdownRef}>
						<button
							onClick={() => {
								if (selection) {
									setShowLabelsDropdown(!showLabelsDropdown);
								}
							}}
							disabled={!selection}
							className="flex cursor-pointer items-center gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-white/5"
						>
							<svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
								/>
							</svg>
							<span>Labels</span>
							<svg
								className={`h-3 w-3 transition-transform ${showLabelsDropdown ? "rotate-180" : ""}`}
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
							</svg>
						</button>

						{/* Dropdown Menu */}
						{showLabelsDropdown && selection && (
							<div className="absolute left-0 top-full z-50 mt-1 min-w-[180px] rounded-lg border border-white/10 bg-[#1a1a1a] p-1.5 shadow-2xl">
								<div className="mb-2 px-2 py-1 text-xs font-medium text-slate-500">Select Label</div>
								<div className="space-y-0.5">
									{labels.map((label) => {
										const colors = LABEL_COLORS[label] || LABEL_COLORS.OTHER;
										return (
											<button
												key={label}
												onClick={() => handleLabelSelect(label)}
												disabled={loading}
												className={`flex w-full cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-left text-xs font-medium transition-all hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-50 ${colors.bg} ${colors.text}`}
											>
												<div className={`h-2 w-2 rounded-full ${colors.border.replace("border-", "bg-").replace("/50", "")}`}></div>
												<span>{label}</span>
											</button>
										);
									})}
								</div>
							</div>
						)}
					</div>

					{/* AI Suggest Button */}
					<button
						onClick={handleGetSuggestions}
						disabled={loadingSuggestions}
						className="flex cursor-pointer items-center gap-2 rounded-md bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
					>
						{loadingSuggestions ? (
							<>
								<div className="h-3 w-3 animate-spin rounded-full border-2 border-slate-600 border-t-white"></div>
								<span>Analyzing...</span>
							</>
						) : (
							<>
								<svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
								</svg>
								<span>AI Suggest</span>
							</>
						)}
					</button>
				</div>
			</div>

			{/* Main content area */}
			<div className="flex flex-1 overflow-hidden">
				{/* Text content - Centered horizontally and vertically */}
				<div className="flex flex-1 items-center justify-center overflow-auto p-8">
					<div className="mx-auto max-w-3xl -mt-16">
						<div
							ref={contentRef}
							onMouseUp={handleTextSelection}
							className="relative whitespace-pre-wrap text-left text-[15px] leading-[1.8] text-slate-300 selection:bg-blue-500/30"
						>
							{renderHighlightedContent()}
						</div>
					</div>
				</div>

				{/* Right sidebar: Annotations & Suggestions */}
				<div className="w-64 shrink-0 overflow-y-auto border-l border-white/5 bg-[#0a0a0a] p-4">
					{/* AI Suggestions */}
					{suggestions.length > 0 && (
						<div className="mb-6">
							<h3 className="mb-3 text-xs font-medium text-slate-500">Suggestions</h3>
							<div className="space-y-2">
								{suggestions.map((suggestion, idx) => {
									const colors = LABEL_COLORS[suggestion.label] || LABEL_COLORS.OTHER;
									return (
										<div key={idx} className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
											<div className="mb-2 flex items-center justify-between">
												<span className={`rounded px-1.5 py-0.5 text-xs font-medium ${colors.bg} ${colors.text}`}>
													{suggestion.label}
												</span>
												<span className="text-xs text-slate-600">{Math.round(suggestion.confidence * 100)}%</span>
											</div>
											<p className="mb-2 text-sm text-slate-400">&quot;{suggestion.text}&quot;</p>
											<div className="flex gap-2">
												<button
													onClick={() => handleAcceptSuggestion(suggestion)}
													className="flex-1 cursor-pointer rounded-md bg-green-500/10 py-1 text-xs text-green-400 transition-all hover:bg-green-500/20"
												>
													Accept
												</button>
												<button
													onClick={() => setSuggestions(suggestions.filter((s) => s !== suggestion))}
													className="flex-1 cursor-pointer rounded-md bg-white/5 py-1 text-xs text-slate-500 transition-all hover:bg-white/10 hover:text-slate-300"
												>
													Dismiss
												</button>
											</div>
										</div>
									);
								})}
							</div>
						</div>
					)}

					{/* Pending Annotations (need approval) */}
					{annotations.filter(a => a.source === "pending_batch").length > 0 && (
						<div className="mb-6">
							<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
								<h3 style={{ fontSize: "12px", fontWeight: "500", color: "#eab308" }}>
									Pending Review ({annotations.filter(a => a.source === "pending_batch").length})
								</h3>
								<div style={{ display: "flex", gap: "6px" }}>
									<button
										onClick={handleAcceptAllPending}
										style={{
											fontSize: "10px",
											padding: "4px 8px",
											borderRadius: "4px",
											backgroundColor: "rgba(74,222,128,0.15)",
											color: "#4ade80",
											border: "none",
											cursor: "pointer",
											fontWeight: "500"
										}}
									>
										✓ All
									</button>
									<button
										onClick={handleRejectAllPending}
										style={{
											fontSize: "10px",
											padding: "4px 8px",
											borderRadius: "4px",
											backgroundColor: "rgba(248,113,113,0.15)",
											color: "#f87171",
											border: "none",
											cursor: "pointer",
											fontWeight: "500"
										}}
									>
										✗ All
									</button>
								</div>
							</div>
							<div className="space-y-2">
								{annotations.filter(a => a.source === "pending_batch").map((ann) => {
									const colors = LABEL_COLORS[ann.label] || LABEL_COLORS.OTHER;
									return (
										<div 
											key={ann.id} 
											className="rounded-lg p-2.5"
											style={{ border: "1px solid rgba(234,179,8,0.3)", backgroundColor: "rgba(234,179,8,0.1)" }}
										>
											<div className="flex items-center justify-between" style={{ gap: "8px" }}>
												<span className={`rounded px-1.5 py-0.5 text-xs font-medium ${colors.bg} ${colors.text}`}>
													{ann.label}
												</span>
												<div style={{ display: "flex", gap: "4px" }}>
													<button
														onClick={() => handleAcceptAnnotation(ann)}
														title="Accept"
														style={{
															display: "flex",
															alignItems: "center",
															justifyContent: "center",
															padding: "6px",
															borderRadius: "4px",
															color: "#4ade80",
															cursor: "pointer",
															backgroundColor: "rgba(74,222,128,0.1)",
															border: "none",
														}}
													>
														<svg style={{ width: "16px", height: "16px" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
														</svg>
													</button>
													<button
														onClick={() => handleRejectAnnotation(ann)}
														title="Reject"
														style={{
															display: "flex",
															alignItems: "center",
															justifyContent: "center",
															padding: "6px",
															borderRadius: "4px",
															color: "#f87171",
															cursor: "pointer",
															backgroundColor: "rgba(248,113,113,0.1)",
															border: "none",
														}}
													>
														<svg style={{ width: "16px", height: "16px" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
														</svg>
													</button>
												</div>
											</div>
											<p className="truncate text-xs" style={{ marginTop: "6px", color: "#94a3b8" }}>&quot;{ann.text}&quot;</p>
										</div>
									);
								})}
							</div>
						</div>
					)}

					{/* Confirmed Annotations */}
					<div>
						<h3 className="mb-3 text-xs font-medium text-slate-500">Annotations ({annotations.filter(a => a.source !== "pending_batch").length})</h3>
						{annotations.filter(a => a.source !== "pending_batch").length === 0 ? (
							<p className="text-xs text-slate-600">Select text to annotate</p>
						) : (
							<div className="space-y-2">
								{annotations.filter(a => a.source !== "pending_batch").map((ann) => {
									const colors = LABEL_COLORS[ann.label] || LABEL_COLORS.OTHER;
									return (
										<div 
											key={ann.id} 
											className="rounded-lg p-2.5"
											style={{ border: "1px solid rgba(255,255,255,0.05)", backgroundColor: "rgba(255,255,255,0.02)" }}
										>
											<div className="flex items-center justify-between" style={{ gap: "8px" }}>
												<span className={`rounded px-1.5 py-0.5 text-xs font-medium ${colors.bg} ${colors.text}`}>
													{ann.label}
												</span>
												<button
													onClick={() => handleDeleteAnnotation(ann)}
													title="Remove annotation"
													style={{
														display: "flex",
														alignItems: "center",
														justifyContent: "center",
														padding: "6px",
														borderRadius: "4px",
														color: "#94a3b8",
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
														e.currentTarget.style.color = "#94a3b8";
													}}
												>
													<svg style={{ width: "16px", height: "16px" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
													</svg>
												</button>
											</div>
											<p className="truncate text-xs" style={{ marginTop: "6px", color: "#94a3b8" }}>&quot;{ann.text}&quot;</p>
										</div>
									);
								})}
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
