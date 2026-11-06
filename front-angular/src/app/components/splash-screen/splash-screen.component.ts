import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { StateService } from '../../services/state.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-splash-screen',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './splash-screen.component.html',
  styleUrl: './splash-screen.component.scss'
})
export class SplashScreenComponent implements OnInit {
  constructor(
    private stateService: StateService,
    private authService: AuthService
  ) {}

  ngOnInit() {
    this.stateService.loadSubjects();
    setTimeout(() => {
      if (this.authService.currentUser) {
        this.stateService.setView('dashboard');
      } else {
        this.stateService.setView('auth');
      }
    }, 1800);
  }

  skip() {
    if (this.authService.currentUser) {
      this.stateService.setView('dashboard');
    } else {
      this.stateService.setView('auth');
    }
  }
}
