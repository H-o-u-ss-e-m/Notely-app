import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { NotebookPage, Subject, Lesson, StructuralHTRResponse } from '../models/models';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  setBaseUrl(url: string) {
    this.baseUrl = url;
  }

  getBaseUrl() {
    return this.baseUrl;
  }

  private getAuthOptions() {
    let token: string | null = null;
    if (typeof window !== 'undefined' && window.sessionStorage) {
      token = sessionStorage.getItem('notely_access_token');
    }
    if (token) {
      return { headers: new HttpHeaders({ 'Authorization': `Bearer ${token}` }) };
    }
    return {};
  }

  login(email: string, pass: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/login`, { email, password: pass });
  }

  register(email: string, pass: string, fullName?: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/register`, {
      email,
      password: pass,
      full_name: fullName,
      role: 'student'
    });
  }

  refresh(refreshToken: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/refresh`, { refresh_token: refreshToken });
  }

  fetchSubjects(): Observable<Subject[]> {
    return this.http.get<Subject[]>(`${this.baseUrl}/courses/subjects`, this.getAuthOptions());
  }

  createSubject(name: string, color: string = "#1E40AF"): Observable<Subject> {
    return this.http.post<Subject>(`${this.baseUrl}/courses/subjects`, { name, color }, this.getAuthOptions());
  }

  updateSubject(subjectId: string, name: string, color: string = "#1E40AF"): Observable<Subject> {
    return this.http.put<Subject>(`${this.baseUrl}/courses/subjects/${subjectId}`, { name, color }, this.getAuthOptions());
  }

  deleteSubject(subjectId: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/courses/subjects/${subjectId}`, this.getAuthOptions());
  }

  createLesson(title: string, subjectId: string, pages: NotebookPage[]): Observable<Lesson> {
    return this.http.post<Lesson>(`${this.baseUrl}/courses/lessons`, {
      title,
      subjectId,
      pages
    }, this.getAuthOptions());
  }

  getLesson(subjectId: string, lessonId: string): Observable<Lesson> {
    return this.http.get<Lesson>(`${this.baseUrl}/courses/subjects/${subjectId}/lessons/${lessonId}`, this.getAuthOptions());
  }

  updateLesson(subjectId: string, lessonId: string, title: string, pages: NotebookPage[]): Observable<Lesson> {
    return this.http.put<Lesson>(`${this.baseUrl}/courses/subjects/${subjectId}/lessons/${lessonId}`, {
      title,
      pages,
      pageCount: pages.length
    }, this.getAuthOptions());
  }

  deleteLesson(subjectId: string, lessonId: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/courses/subjects/${subjectId}/lessons/${lessonId}`, this.getAuthOptions());
  }

  recognizeStructuralPages(pages: NotebookPage[], width: number, height: number, subject: string, lessonTitle: string, language: string = 'fr'): Observable<StructuralHTRResponse> {
    const pagePayload = pages.map(p => ({
      pageNumber: p.pageNumber,
      strokes: p.strokes,
      width: p.width || width,
      height: p.height || height
    }));
    return this.http.post<StructuralHTRResponse>(`${this.baseUrl}/structural-htr`, {
      pages: pagePayload,
      canvasWidth: width,
      canvasHeight: height,
      subject,
      lessonTitle,
      language
    }, this.getAuthOptions());
  }

  exportPdf(subject: string, lessonTitle: string, elements: any[]): Observable<Blob> {
    return this.http.post(`${this.baseUrl}/export-pdf`, {
      subject,
      lessonTitle,
      elements
    }, { ...this.getAuthOptions(), responseType: 'blob' });
  }

  logout(refreshToken: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/logout`, { refresh_token: refreshToken }, this.getAuthOptions());
  }

  logoutAll(): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/logout-all`, {}, this.getAuthOptions());
  }

  patchPageStrokes(pageId: string, baseVersion: number, added: any[], removedClientIds: string[] = []): Observable<{ pageId: string; version: number }> {
    return this.http.patch<{ pageId: string; version: number }>(
      `${this.baseUrl}/pages/${pageId}/strokes`,
      { baseVersion, added, removedClientIds },
      this.getAuthOptions()
    );
  }

  getPageStrokes(pageId: string): Observable<{ pageId: string; version: number; strokes: any[] }> {
    return this.http.get<{ pageId: string; version: number; strokes: any[] }>(
      `${this.baseUrl}/pages/${pageId}/strokes`,
      this.getAuthOptions()
    );
  }

  exportRawPdfPages(pages: NotebookPage[], width: number, height: number, subject: string, lessonTitle: string): Observable<Blob> {
    const pagePayload = pages.map(p => ({
      pageNumber: p.pageNumber,
      strokes: p.strokes,
      width: p.width || width,
      height: p.height || height
    }));
    return this.http.post(`${this.baseUrl}/export-pdf-raw`, {
      pages: pagePayload,
      canvasWidth: width,
      canvasHeight: height,
      subject,
      lessonTitle
    }, { ...this.getAuthOptions(), responseType: 'blob' });
  }

  sendFeedback(feedbackData: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/ocr/feedback`, feedbackData, this.getAuthOptions());
  }

  // --- FLASHCARDS SM-2 (Partie 6.7) ---
  generateFlashcardsFromOcr(lessonId: string | null, elements: any[]) {
    return this.http.post<any[]>(
      `${this.baseUrl}/flashcards/from-ocr`,
      { lesson_id: lessonId, elements },
      this.getAuthOptions()
    );
  }

  getDueFlashcards() {
    return this.http.get<any[]>(`${this.baseUrl}/flashcards/due`, this.getAuthOptions());
  }

  reviewFlashcard(cardId: string, rating: number) {
    return this.http.post<any>(
      `${this.baseUrl}/flashcards/${cardId}/review`,
      { rating },
      this.getAuthOptions()
    );
  }

  getFlashcards(lessonId?: string) {
    const url = lessonId ? `${this.baseUrl}/flashcards?lesson_id=${lessonId}` : `${this.baseUrl}/flashcards`;
    return this.http.get<any[]>(url, this.getAuthOptions());
  }
}
