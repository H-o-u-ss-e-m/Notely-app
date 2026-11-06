import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { StateService } from '../../services/state.service';
import { ToastService } from '../../services/toast.service';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './auth.component.html',
  styleUrl: './auth.component.scss'
})
export class AuthComponent {
  authMode: 'login' | 'register' = 'login';
  email: string = '';
  password: string = '';
  displayName: string = '';
  loading: boolean = false;
  errorMessage: string = '';

  constructor(
    private authService: AuthService,
    private stateService: StateService,
    private toastService: ToastService
  ) {}

  fillDemo(email: string, pass: string, name: string) {
    this.email = email;
    this.password = pass;
    this.displayName = name;
    this.errorMessage = '';
  }

  async submit() {
    if (!this.email || !this.password) {
      this.errorMessage = 'Veuillez remplir tous les champs obligatoires.';
      return;
    }

    this.loading = true;
    this.errorMessage = '';

    try {
      if (this.authMode === 'login') {
        await this.authService.login(this.email, this.password);
        this.toastService.success('Connexion réussie', 'Bienvenue sur Notely !');
      } else {
        await this.authService.register(this.email, this.password, this.displayName || 'Étudiant');
        this.toastService.success('Compte créé', 'Votre compte Notely est prêt !');
      }
      this.stateService.loadSubjects();
      this.stateService.setView('dashboard');
    } catch (err: any) {
      this.errorMessage = err.message || 'Erreur lors de l\'authentification.';
    } finally {
      this.loading = false;
    }
  }
}
