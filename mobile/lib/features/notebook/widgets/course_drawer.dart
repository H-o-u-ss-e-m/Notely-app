import 'package:flutter/material.dart';
import '../../../models/course_model.dart';
import '../../../core/config/env_config.dart';

class CourseDrawer extends StatelessWidget {
  final List<SubjectModel> subjects;
  final SubjectModel? activeSubject;
  final LessonModel? activeLesson;
  final Function(SubjectModel subject, LessonModel lesson) onSelectLesson;
  final VoidCallback onCreateSubject;
  final VoidCallback onCreateLesson;
  final VoidCallback onOpenServerSettings;
  /// Appelé quand l'utilisateur clique sur "Accueil" dans le Drawer.
  final VoidCallback onGoHome;

  const CourseDrawer({
    super.key,
    required this.subjects,
    this.activeSubject,
    this.activeLesson,
    required this.onSelectLesson,
    required this.onCreateSubject,
    required this.onCreateLesson,
    required this.onOpenServerSettings,
    required this.onGoHome,
  });

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: Column(
        children: [
          // ── En-tête ───────────────────────────────────────────────────────
          DrawerHeader(
            decoration: const BoxDecoration(color: Color(0xFF1E40AF)),
            child: Row(
              children: [
                const CircleAvatar(
                  radius: 26,
                  backgroundColor: Colors.white24,
                  child: Icon(Icons.menu_book, color: Colors.white, size: 28),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Smart Notebook',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Gestionnaire de Cours',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.8),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // ── Bouton Accueil (Dashboard) ────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: ListTile(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              tileColor: const Color(0xFF1E40AF).withValues(alpha: 0.08),
              leading: const Icon(Icons.home_rounded, color: Color(0xFF1E40AF), size: 26),
              title: const Text(
                'Accueil — Dashboard',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: Color(0xFF1E40AF),
                ),
              ),
              subtitle: const Text(
                'Revenir à la liste des cours',
                style: TextStyle(fontSize: 11),
              ),
              onTap: () {
                Navigator.pop(context); // Ferme le drawer
                onGoHome();             // Navigue vers le Dashboard
              },
            ),
          ),

          const Divider(height: 12),

          // ── Actions rapides ───────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onCreateLesson,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('Nouveau Cours', style: TextStyle(fontSize: 12)),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  tooltip: 'Ajouter Matière',
                  icon: const Icon(Icons.create_new_folder_outlined),
                  onPressed: onCreateSubject,
                ),
              ],
            ),
          ),

          const Divider(),

          // ── Liste des Matières et Leçons ──────────────────────────────────
          Expanded(
            child: ListView.builder(
              itemCount: subjects.length,
              itemBuilder: (context, sIdx) {
                final subject = subjects[sIdx];
                final hexColor = subject.color.replaceFirst('#', '');
                final colorVal = Color(int.parse('ff$hexColor', radix: 16));

                return ExpansionTile(
                  leading: CircleAvatar(radius: 10, backgroundColor: colorVal),
                  title: Text(
                    subject.name,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  children: subject.lessons.map((lesson) {
                    final isSelected = activeLesson?.id == lesson.id;
                    return ListTile(
                      contentPadding: const EdgeInsets.only(left: 48, right: 16),
                      selected: isSelected,
                      selectedTileColor: Colors.blue.shade50,
                      leading: Icon(
                        Icons.description_outlined,
                        size: 18,
                        color: isSelected ? Colors.blue : Colors.grey.shade600,
                      ),
                      title: Text(
                        lesson.title,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          color: isSelected ? Colors.blue.shade900 : Colors.black87,
                        ),
                      ),
                      subtitle: Text(
                        lesson.updatedAt,
                        style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
                      ),
                      onTap: () {
                        onSelectLesson(subject, lesson);
                        Navigator.pop(context);
                      },
                    );
                  }).toList(),
                );
              },
            ),
          ),

          const Divider(),

          // ── Footer Connexion ──────────────────────────────────────────────
          ListTile(
            leading: const Icon(Icons.settings_ethernet, color: Colors.blue),
            title: const Text('Connexion Serveur PC', style: TextStyle(fontSize: 13)),
            subtitle: Text(
              EnvConfig.baseUrl.contains('127.0.0.1') ? 'Câble USB ADB' : EnvConfig.baseUrl,
              style: const TextStyle(fontSize: 11),
            ),
            onTap: onOpenServerSettings,
          ),
        ],
      ),
    );
  }
}
