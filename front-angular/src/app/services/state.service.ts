import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { ApiService } from './api.service';
import { ToastService } from './toast.service';
import { Subject, Lesson, NotebookPage } from '../models/models';

@Injectable({
  providedIn: 'root'
})
export class StateService {
  private currentViewSubject = new BehaviorSubject<'splash' | 'auth' | 'dashboard' | 'editor'>('splash');
  currentView$ = this.currentViewSubject.asObservable();

  private subjectsSubject = new BehaviorSubject<Subject[]>([]);
  subjects$ = this.subjectsSubject.asObservable();

  private currentSubjectSubject = new BehaviorSubject<Subject | null>(null);
  currentSubject$ = this.currentSubjectSubject.asObservable();

  private currentLessonSubject = new BehaviorSubject<Lesson | null>(null);
  currentLesson$ = this.currentLessonSubject.asObservable();

  private activeSubjectFilterSubject = new BehaviorSubject<string>('all');
  activeSubjectFilter$ = this.activeSubjectFilterSubject.asObservable();

  private searchQuerySubject = new BehaviorSubject<string>('');
  searchQuery$ = this.searchQuerySubject.asObservable();

  private lastSavedTimeSubject = new BehaviorSubject<string>('');
  lastSavedTime$ = this.lastSavedTimeSubject.asObservable();

  private isSavingSubject = new BehaviorSubject<boolean>(false);
  isSaving$ = this.isSavingSubject.asObservable();

  // 4 états Partie 4.2
  private saveStateSubject = new BehaviorSubject<'saved' | 'saving' | 'dirty' | 'error'>('saved');
  saveState$ = this.saveStateSubject.asObservable();

  private autoSaveTimer: any = null;
  private autoSaveDebounceTimer: any = null;
  private hasUnsavedChanges: boolean = false;

  constructor(
    private apiService: ApiService,
    private toastService: ToastService
  ) {
    this.initAutoSaveTimer();
  }

  setView(view: 'splash' | 'auth' | 'dashboard' | 'editor') {
    this.currentViewSubject.next(view);
  }

  getView(): 'splash' | 'auth' | 'dashboard' | 'editor' {
    return this.currentViewSubject.value;
  }

  loadSubjects() {
    this.apiService.fetchSubjects().subscribe({
      next: (subs) => {
        this.subjectsSubject.next(subs);
        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.setItem('notely_subjects', JSON.stringify(subs));
        }
      },
      error: () => {
        if (typeof window !== 'undefined' && window.localStorage) {
          const cached = localStorage.getItem('notely_subjects');
          if (cached) {
            try {
              this.subjectsSubject.next(JSON.parse(cached));
            } catch (e) {
              console.error(e);
            }
          }
        }
      }
    });
  }

  setSubjects(subs: Subject[]) {
    this.subjectsSubject.next(subs);
  }

  getSubjects(): Subject[] {
    return this.subjectsSubject.value;
  }

  setFilter(filter: string) {
    this.activeSubjectFilterSubject.next(filter);
  }

  setSearchQuery(q: string) {
    this.searchQuerySubject.next(q);
  }

  openCourse(subject: Subject, lesson: Lesson) {
    this.currentSubjectSubject.next(subject);
    this.currentLessonSubject.next(lesson);
    this.setView('editor');
    this.hasUnsavedChanges = false;

    // Charger les détails en direct depuis l'API Backend / Firebase (Sync Web/Mobile)
    this.apiService.getLesson(subject.id, lesson.id).subscribe({
      next: (freshLesson) => {
        if (freshLesson && freshLesson.pages) {
          this.currentLessonSubject.next(freshLesson);
        }
      },
      error: (err) => console.warn('Sync avertissement : utilisation de la version locale du cours.', err)
    });
  }

  markChangesDirty(onDebounceTrigger?: () => void) {
    this.hasUnsavedChanges = true;
    this.saveStateSubject.next('dirty');

    // Autosave débouncé à 2 secondes (Partie 4.3)
    if (onDebounceTrigger && typeof window !== 'undefined') {
      if (this.autoSaveDebounceTimer) clearTimeout(this.autoSaveDebounceTimer);
      this.autoSaveDebounceTimer = setTimeout(() => {
        if (this.hasUnsavedChanges && this.currentViewSubject.value === 'editor') {
          onDebounceTrigger();
        }
      }, 2000);
    }
  }

  getCurrentLesson(): Lesson | null {
    return this.currentLessonSubject.value;
  }

  getCurrentSubject(): Subject | null {
    return this.currentSubjectSubject.value;
  }

  updateSubject(subjectId: string, name: string, color: string) {
    this.apiService.updateSubject(subjectId, name, color).subscribe({
      next: () => {
        this.loadSubjects();
        this.toastService.success('Espace modifié', `Espace "${name}" mis à jour.`);
      },
      error: () => this.toastService.error('Erreur', 'Impossible de modifier l\'espace.')
    });
  }

  deleteSubject(subjectId: string, name: string) {
    this.apiService.deleteSubject(subjectId).subscribe({
      next: () => {
        this.loadSubjects();
        this.toastService.success('Espace supprimé', `L'espace "${name}" a été supprimé.`);
      },
      error: () => this.toastService.error('Erreur', 'Impossible de supprimer l\'espace.')
    });
  }

  deleteLesson(subjectId: string, lessonId: string, title: string) {
    this.apiService.deleteLesson(subjectId, lessonId).subscribe({
      next: () => {
        this.loadSubjects();
        this.toastService.success('Cours supprimé', `Le cours "${title}" a été supprimé.`);
      },
      error: () => this.toastService.error('Erreur', 'Impossible de supprimer le cours.')
    });
  }

  renameLesson(subjectId: string, lessonId: string, newTitle: string, pages: NotebookPage[] = []) {
    this.apiService.updateLesson(subjectId, lessonId, newTitle, pages).subscribe({
      next: (fresh) => {
        this.loadSubjects();
        const curLesson = this.currentLessonSubject.value;
        if (curLesson && curLesson.id === lessonId) {
          this.currentLessonSubject.next({ ...curLesson, title: newTitle });
        }
        this.toastService.success('Cours renommé', `Nouveau titre : "${newTitle}".`);
      },
      error: () => this.toastService.error('Erreur', 'Impossible de renommer le cours.')
    });
  }

  saveCurrentLesson(pages: NotebookPage[]): void {
    const subj = this.currentSubjectSubject.value;
    const les = this.currentLessonSubject.value;
    if (!subj || !les) return;

    if (this.autoSaveDebounceTimer) {
      clearTimeout(this.autoSaveDebounceTimer);
      this.autoSaveDebounceTimer = null;
    }

    this.isSavingSubject.next(true);
    this.saveStateSubject.next('saving');
    this.apiService.updateLesson(subj.id, les.id, les.title, pages).subscribe({
      next: (updated) => {
        this.isSavingSubject.next(false);
        this.hasUnsavedChanges = false;
        this.saveStateSubject.next('saved');
        if (updated) {
          this.currentLessonSubject.next(updated);
        }
        const now = new Date();
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        this.lastSavedTimeSubject.next(timeStr);
        this.toastService.success('Enregistré', `Le cours "${les.title}" a été sauvegardé.`);
        this.loadSubjects();
      },
      error: () => {
        this.isSavingSubject.next(false);
        this.saveStateSubject.next('error');
        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.setItem(`notely_course_${les.id}`, JSON.stringify(pages));
        }
        const now = new Date();
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        this.lastSavedTimeSubject.next(timeStr);
        this.toastService.error('Erreur sauvegarde', 'Les modifications sont conservées en local.');
      }
    });
  }

  private initAutoSaveTimer() {
    if (typeof window === 'undefined') return;
    if (this.autoSaveTimer) clearInterval(this.autoSaveTimer);

    this.autoSaveTimer = setInterval(() => {
      if (this.currentViewSubject.value === 'editor' && this.hasUnsavedChanges) {
        const les = this.currentLessonSubject.value;
        const subj = this.currentSubjectSubject.value;
        if (subj && les) {
          const pages = les.pages || [];
          this.apiService.updateLesson(subj.id, les.id, les.title, pages).subscribe({
            next: (updated) => {
              this.hasUnsavedChanges = false;
              if (updated) this.currentLessonSubject.next(updated);
              const now = new Date();
              const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
              this.lastSavedTimeSubject.next(timeStr);
              this.toastService.info('Auto-Save Notely', `Enregistrement automatique Firebase (${timeStr}).`);
            },
            error: () => {
              const now = new Date();
              const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
              this.lastSavedTimeSubject.next(timeStr);
            }
          });
        }
      }
    }, 5 * 60 * 1000);
  }
}
