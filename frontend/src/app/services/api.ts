const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export type Document = {
	id: string;
	filename: string;
	title: string;
	status: "pending" | "in_progress" | "completed" | "reviewed";
	created_at: string;
	content?: string;
};

export type Annotation = {
	id: string;
	document_id: string;
	label: string;
	span_start: number;
	span_end: number;
	text?: string;
	confidence: number;
	source: "manual" | "ai";
	created_at: string;
};

export const documentAPI = {
	async list(): Promise<Document[]> {
		const response = await fetch(`${API_BASE_URL}/documents`);
		if (!response.ok) throw new Error("Failed to fetch documents");
		return response.json();
	},

	async get(documentId: string): Promise<Document> {
		const response = await fetch(`${API_BASE_URL}/documents/${documentId}`);
		if (!response.ok) throw new Error("Failed to fetch document");
		return response.json();
	},

	async getContent(documentId: string): Promise<{ content: string }> {
		const response = await fetch(`${API_BASE_URL}/documents/${documentId}/content`);
		if (!response.ok) throw new Error("Failed to fetch document content");
		return response.json();
	},

	async upload(file: File): Promise<Document> {
		const formData = new FormData();
		formData.append("file", file);

		const response = await fetch(`${API_BASE_URL}/documents/upload`, {
			method: "POST",
			body: formData,
		});

		if (!response.ok) throw new Error("Failed to upload document");
		return response.json();
	},

	async batchUpload(files: File[]): Promise<Document[]> {
		const formData = new FormData();
		files.forEach((file) => formData.append("files", file));

		const response = await fetch(`${API_BASE_URL}/documents/batch-upload`, {
			method: "POST",
			body: formData,
		});

		if (!response.ok) throw new Error("Failed to upload documents");
		return response.json();
	},

	async updateStatus(documentId: string, status: Document["status"]): Promise<Document> {
		const response = await fetch(`${API_BASE_URL}/documents/${documentId}/status`, {
			method: "PATCH",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ status }),
		});

		if (!response.ok) throw new Error("Failed to update document status");
		return response.json();
	},

	async delete(documentId: string): Promise<void> {
		const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
			method: "DELETE",
		});

		if (!response.ok) throw new Error("Failed to delete document");
	},
};

export type Suggestion = {
	text?: string;
	label: string;
	span_start?: number;
	span_end?: number;
	confidence: number;
	source: string;
};

export type SuggestResponse = {
	suggestions: Suggestion[];
	exemplars_used: number;
	ml_available: boolean;
};

export const annotationAPI = {
	async create(
		documentId: string,
		annotation: Omit<Annotation, "id" | "document_id" | "created_at">
	): Promise<Annotation> {
		const response = await fetch(`${API_BASE_URL}/annotations/documents/${documentId}`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(annotation),
		});

		if (!response.ok) throw new Error("Failed to create annotation");
		return response.json();
	},

	async listByDocument(documentId: string): Promise<Annotation[]> {
		const response = await fetch(`${API_BASE_URL}/annotations/documents/${documentId}`);
		if (!response.ok) throw new Error("Failed to fetch annotations");
		return response.json();
	},

	async update(
		documentId: string,
		annotationId: string,
		updates: Partial<Pick<Annotation, "label" | "span_start" | "span_end" | "text" | "confidence">>
	): Promise<Annotation> {
		const response = await fetch(
			`${API_BASE_URL}/annotations/documents/${documentId}/${annotationId}`,
			{
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(updates),
			}
		);

		if (!response.ok) throw new Error("Failed to update annotation");
		return response.json();
	},

	async delete(documentId: string, annotationId: string): Promise<void> {
		const response = await fetch(
			`${API_BASE_URL}/annotations/documents/${documentId}/${annotationId}`,
			{
				method: "DELETE",
			}
		);

		if (!response.ok) throw new Error("Failed to delete annotation");
	},

	async accept(documentId: string, annotationId: string): Promise<{ status: string }> {
		const response = await fetch(
			`${API_BASE_URL}/annotations/documents/${documentId}/${annotationId}/accept`,
			{
				method: "POST",
			}
		);

		if (!response.ok) throw new Error("Failed to accept annotation");
		return response.json();
	},

	async reject(documentId: string, annotationId: string): Promise<{ status: string }> {
		const response = await fetch(
			`${API_BASE_URL}/annotations/documents/${documentId}/${annotationId}/reject`,
			{
				method: "POST",
			}
		);

		if (!response.ok) throw new Error("Failed to reject annotation");
		return response.json();
	},

	async suggest(
		documentId: string,
		options?: { task?: string; labels?: string[]; top_k?: number }
	): Promise<SuggestResponse> {
		const response = await fetch(
			`${API_BASE_URL}/annotations/documents/${documentId}/suggest`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					task: options?.task || "ner",
					labels: options?.labels,
					top_k: options?.top_k || 3,
				}),
			}
		);

		if (!response.ok) throw new Error("Failed to get suggestions");
		return response.json();
	},

	async approve(documentId: string, annotationId: string, context?: string): Promise<void> {
		const response = await fetch(
			`${API_BASE_URL}/annotations/documents/${documentId}/${annotationId}/approve`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ context }),
			}
		);

		if (!response.ok) throw new Error("Failed to approve annotation");
	},
};
