import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { StateService } from '../../services/state.service';
import { ApiService } from '../../services/api.service';
import { ToastService } from '../../services/toast.service';
import { Subject, Lesson } from '../../models/models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  showNewSpaceModal: boolean = false;
  showNewCourseModal: boolean = false;
  showEditSpaceModal: boolean = false;
  showEditCourseModal: boolean = false;

  newSpaceName: string = '';
  newSpaceColor: string = '#1E40AF';
  newCourseTitle: string = '';
  newCourseSubjectId: string = '';

  editSpaceId: string = '';
  editSpaceName: string = '';
  editSpaceColor: string = '#1E40AF';

  editCourseSubjectId: string = '';
  editCourseLessonId: string = '';
  editCourseTitle: string = '';

  colors = ['#1E40AF', '#DC2626', '#15803D', '#7C3AED', '#D97706', '#0D9488'];

  constructor(
    public stateService: StateService,
    private apiService: ApiService,
    private toastService: ToastService
  ) {}

  ngOnInit() {
    this.stateService.loadSubjects();
  }

  get filteredCourses(): { subject: Subject; lesson: Lesson }[] {
    const subs = this.stateService.getSubjects();
    const filter = (this.stateService as any).activeSubjectFilterSubject?.value || 'all';
    const query = ((this.stateService as any).searchQuerySubject?.value || '').toLowerCase();

    const list: { subject: Subject; lesson: Lesson }[] = [];
    for (const s of subs) {
      if (filter !== 'all' && s.id !== filter) continue;
      for (const l of s.lessons) {
        if (query && !l.title.toLowerCase().includes(query) && !s.name.toLowerCase().includes(query)) {
          continue;
        }
        list.push({ subject: s, lesson: l });
      }
    }
    return list;
  }

  openCourse(subject: Subject, lesson: Lesson) {
    this.stateService.openCourse(subject, lesson);
  }

  openNewSpaceDialog() {
    this.newSpaceName = '';
    this.newSpaceColor = '#1E40AF';
    this.showNewSpaceModal = true;
  }

  openNewCourseDialog(subjectId?: string) {
    this.newCourseTitle = '';
    const subs = this.stateService.getSubjects();
    this.newCourseSubjectId = subjectId || (subs.length > 0 ? subs[0].id : '');
    this.showNewCourseModal = true;
  }

  createSpace() {
    if (!this.newSpaceName.trim()) return;
    this.apiService.createSubject(this.newSpaceName.trim(), this.newSpaceColor).subscribe({
      next: (created) => {
        const subs = [...this.stateService.getSubjects(), created];
        this.stateService.setSubjects(subs);
        this.showNewSpaceModal = false;
        this.toastService.success('Espace créé', `Espace "${created.name}" créé.`);
      },
      error: () => {
        const fallback: Subject = {
          id: `subj-${Date.now()}`,
          name: this.newSpaceName.trim(),
          color: this.newSpaceColor,
          lessons: []
        };
        const subs = [...this.stateService.getSubjects(), fallback];
        this.stateService.setSubjects(subs);
        this.showNewSpaceModal = false;
        this.toastService.info('Espace créé (local)', `Espace "${fallback.name}" créé.`);
      }
    });
  }

  openEditSpaceDialog(subject: Subject, e?: Event) {
    if (e) e.stopPropagation();
    this.editSpaceId = subject.id;
    this.editSpaceName = subject.name;
    this.editSpaceColor = subject.color;
    this.showEditSpaceModal = true;
  }

  updateSpace() {
    if (!this.editSpaceName.trim() || !this.editSpaceId) return;
    this.stateService.updateSubject(this.editSpaceId, this.editSpaceName.trim(), this.editSpaceColor);
    this.showEditSpaceModal = false;
  }

  deleteSpace(subject: Subject, e?: Event) {
    if (e) e.stopPropagation();
    if (confirm(`Voulez-vous vraiment supprimer l'espace "${subject.name}" et tous ses cours ?`)) {
      this.stateService.deleteSubject(subject.id, subject.name);
    }
  }

  openEditCourseDialog(subject: Subject, lesson: Lesson, e?: Event) {
    if (e) e.stopPropagation();
    this.editCourseSubjectId = subject.id;
    this.editCourseLessonId = lesson.id;
    this.editCourseTitle = lesson.title;
    this.showEditCourseModal = true;
  }

  updateCourse() {
    if (!this.editCourseTitle.trim() || !this.editCourseSubjectId || !this.editCourseLessonId) return;
    this.stateService.renameLesson(this.editCourseSubjectId, this.editCourseLessonId, this.editCourseTitle.trim());
    this.showEditCourseModal = false;
  }

  deleteCourse(subject: Subject, lesson: Lesson, e?: Event) {
    if (e) e.stopPropagation();
    if (confirm(`Voulez-vous vraiment supprimer le cours "${lesson.title}" ?`)) {
      this.stateService.deleteLesson(subject.id, lesson.id, lesson.title);
    }
  }

  createCourse() {
    if (!this.newCourseTitle.trim() || !this.newCourseSubjectId) return;
    const subs = this.stateService.getSubjects();
    const targetSubj = subs.find(s => s.id === this.newCourseSubjectId);
    if (!targetSubj) return;

    this.apiService.createLesson(this.newCourseTitle.trim(), this.newCourseSubjectId, []).subscribe({
      next: (created) => {
        targetSubj.lessons.unshift(created);
        this.stateService.setSubjects([...subs]);
        this.showNewCourseModal = false;
        this.openCourse(targetSubj, created);
      },
      error: () => {
        const fallback: Lesson = {
          id: `les-${Date.now()}`,
          title: this.newCourseTitle.trim(),
          updatedAt: new Date().toISOString().split('T')[0],
          pages: [{ id: 'p-1', pageNumber: 1, strokes: [], redoStack: [] }]
        };
        targetSubj.lessons.unshift(fallback);
        this.stateService.setSubjects([...subs]);
        this.showNewCourseModal = false;
        this.openCourse(targetSubj, fallback);
      }
    });
  }
}
