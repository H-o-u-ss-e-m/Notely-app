export interface Point {
  x: number;
  y: number;
  timestamp?: number;
  pressure?: number;
}

export interface BoundingBox {
  xMin: number;
  yMin: number;
  xMax: number;
  yMax: number;
}

export interface Stroke {
  id: string;
  points: Point[];
  startTime: number;
  endTime: number;
  color?: string;
  width?: number;
  tool?: string;         // 'pen', 'diagram', 'eraser'
  contentType?: string;  // 'normal', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
  pointerType?: string;
  bbox?: BoundingBox;
}

export interface NotebookPage {
  id: string;
  pageNumber: number;
  strokes: Stroke[];
  redoStack: Stroke[];
  width?: number;
  height?: number;
}

export interface Lesson {
  id: string;
  title: string;
  updatedAt: string;
  pageCount?: number;
  pages?: NotebookPage[];
}

export interface Subject {
  id: string;
  name: string;
  color: string;
  icon?: string;
  description?: string;
  lessons: Lesson[];
}

export interface WordResult {
  index: number;
  text: string;
  confidence: number;
  calibrated?: boolean;
  alternatives?: string[];
  bbox?: number[];
  corrected?: boolean;
  original?: string;
  source?: string;
}

export interface StructuralElement {
  id: number;
  type: string;
  text: string;
  confidence: number;
  calibrated?: boolean;
  min_word_confidence?: number;
  words?: WordResult[];
  alternatives?: string[];
  thumbnail?: string;
  bbox: number[];
  image_base64?: string;
  stroke_ids?: string[];
  pageNumber?: number;
  source?: string;
  stroke_fingerprint?: string;
}

export interface StructuralHTRResponse {
  success: boolean;
  processingTimeMs: number;
  subject: string;
  lessonTitle: string;
  elements: StructuralElement[];
  fullMarkdown: string;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
}

export interface DialogConfig {
  title: string;
  message: string;
  type: 'confirm' | 'info' | 'danger';
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel?: () => void;
}
