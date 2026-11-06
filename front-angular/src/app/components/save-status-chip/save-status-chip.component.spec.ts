import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SaveStatusChipComponent } from './save-status-chip.component';

describe('SaveStatusChipComponent (Partie 4.2)', () => {
  let component: SaveStatusChipComponent;
  let fixture: ComponentFixture<SaveStatusChipComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SaveStatusChipComponent]
    }).compileComponents();
  });

  it('renders "Enregistré" in saved state', () => {
    fixture = TestBed.createComponent(SaveStatusChipComponent);
    component = fixture.componentInstance;
    component.status = 'saved';
    component.lastSavedTime = '18:15';
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Enregistré (18:15)');
    expect(el.querySelector('.save-status-chip')?.classList.contains('saved')).toBe(true);
  });

  it('renders "Enregistrement…" and spinner in saving state', () => {
    fixture = TestBed.createComponent(SaveStatusChipComponent);
    component = fixture.componentInstance;
    component.status = 'saving';
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Enregistrement…');
    expect(el.querySelector('.spinner')).toBeTruthy();
  });

  it('renders "Modifications non enregistrées" in dirty state', () => {
    fixture = TestBed.createComponent(SaveStatusChipComponent);
    component = fixture.componentInstance;
    component.status = 'dirty';
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Modifications non enregistrées');
    expect(el.querySelector('.save-status-chip')?.classList.contains('dirty')).toBe(true);
  });

  it('renders "Échec de l\'enregistrement" in error state', () => {
    fixture = TestBed.createComponent(SaveStatusChipComponent);
    component = fixture.componentInstance;
    component.status = 'error';
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Échec de l\'enregistrement');
    expect(el.querySelector('.save-status-chip')?.classList.contains('error')).toBe(true);
  });
});
