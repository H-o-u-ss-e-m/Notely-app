import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type SaveState = 'saved' | 'saving' | 'dirty' | 'error';

@Component({
  selector: 'app-save-status-chip',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="save-status-chip" [ngClass]="status" [attr.title]="tooltipText">
      <span class="status-indicator">
        <span *ngIf="status === 'saving'" class="spinner"></span>
        <span *ngIf="status !== 'saving'" class="dot"></span>
      </span>
      <span class="status-label">{{ displayText }}</span>
    </div>
  `,
  styles: [`
    .save-status-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 500;
      transition: all 0.2s ease;
      user-select: none;
    }
    .status-indicator {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 8px;
      height: 8px;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .spinner {
      width: 8px;
      height: 8px;
      border: 2px solid currentColor;
      border-right-color: transparent;
      border-radius: 50%;
      animation: spin 0.75s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    /* 4 états Partie 4.2 */
    .save-status-chip.saved {
      background: rgba(34, 197, 94, 0.12);
      color: #16a34a;
      border: 1px solid rgba(34, 197, 94, 0.25);
    }
    .save-status-chip.saved .dot {
      background: #16a34a;
    }
    .save-status-chip.saving {
      background: rgba(59, 130, 246, 0.12);
      color: #2563eb;
      border: 1px solid rgba(59, 130, 246, 0.25);
    }
    .save-status-chip.dirty {
      background: rgba(245, 158, 11, 0.12);
      color: #d97706;
      border: 1px solid rgba(245, 158, 11, 0.25);
    }
    .save-status-chip.dirty .dot {
      background: #d97706;
    }
    .save-status-chip.error {
      background: rgba(239, 68, 68, 0.12);
      color: #dc2626;
      border: 1px solid rgba(239, 68, 68, 0.25);
    }
    .save-status-chip.error .dot {
      background: #dc2626;
    }
  `]
})
export class SaveStatusChipComponent {
  @Input() status: SaveState = 'saved';
  @Input() lastSavedTime?: string;
  @Input() errorMessage?: string;

  get displayText(): string {
    switch (this.status) {
      case 'saved':
        return this.lastSavedTime ? `Enregistré (${this.lastSavedTime})` : 'Enregistré';
      case 'saving':
        return 'Enregistrement…';
      case 'dirty':
        return 'Modifications non enregistrées';
      case 'error':
        return 'Échec de l\'enregistrement';
    }
  }

  get tooltipText(): string {
    switch (this.status) {
      case 'saved':
        return 'Toutes les modifications sont enregistrées sur le serveur.';
      case 'saving':
        return 'Synchronisation des modifications avec le serveur en cours…';
      case 'dirty':
        return 'Des tracés sont en mémoire locale et seront synchronisés automatiquement.';
      case 'error':
        return this.errorMessage || 'Impossible de contacter le serveur. Les données restent en local.';
    }
  }
}
