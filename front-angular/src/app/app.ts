import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { StateService } from './services/state.service';
import { ToastService } from './services/toast.service';
import { NavbarComponent } from './components/navbar/navbar.component';
import { SplashScreenComponent } from './components/splash-screen/splash-screen.component';
import { AuthComponent } from './components/auth/auth.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { NotebookEditorComponent } from './components/notebook-editor/notebook-editor.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    NavbarComponent,
    SplashScreenComponent,
    AuthComponent,
    DashboardComponent,
    NotebookEditorComponent
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  constructor(
    public stateService: StateService,
    public toastService: ToastService
  ) {}

  ngOnInit() {
    this.stateService.loadSubjects();
  }
}
