export type AnnotationSpan = {
	start: number;
	end: number;
	label: string;
};

export type AnnotationSuggestion = {
	spans?: AnnotationSpan[];
	labels?: Record<string, unknown>;
	confidence?: number | null;
	rationale?: string | null;
};

export type AnnotateRequest = {
	input_text: string;
	task: "ner" | "classification" | "json";
	schema?: Record<string, unknown>;
	max_suggestions?: number;
};

export type AnnotateResponse = {
	suggestions: AnnotationSuggestion[];
};
