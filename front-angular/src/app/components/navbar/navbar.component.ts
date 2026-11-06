import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { StateService } from '../../services/state.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.scss'
})
export class NavbarComponent {
  constructor(
    public stateService: StateService,
    public authService: AuthService
  ) {}

  goDashboard() {
    this.stateService.setView('dashboard');
  }

  logout() {
    this.authService.logout();
    this.stateService.setView('auth');
  }
}
