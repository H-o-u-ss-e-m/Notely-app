import 'package:flutter/material.dart';
import '../../../models/course_model.dart';
import '../../../core/network/api_client.dart';
import '../notebook/screens/notebook_screen.dart';
import '../auth/auth_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<SubjectModel> _subjects = [];
  bool _isLoading = true;
  String _searchQuery = '';
  String? _selectedSubjectId; // null = Tous les espaces

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final subs = await ApiClient.fetchSubjects();
    if (!mounted) return;
    setState(() {
      _subjects = subs;
      _isLoading = false;
    });
  }

  List<Map<String, dynamic>> get _filteredCourses {
    final list = <Map<String, dynamic>>[];
    for (final subj in _subjects) {
      if (_selectedSubjectId != null && subj.id != _selectedSubjectId) continue;
      for (final les in subj.lessons) {
        if (_searchQuery.isNotEmpty) {
          final q = _searchQuery.toLowerCase();
          final matchesTitle = les.title.toLowerCase().contains(q);
          final matchesSubj = subj.name.toLowerCase().contains(q);
          if (!matchesTitle && !matchesSubj) continue;
        }
        list.add({
          'subject': subj,
          'lesson': les,
        });
      }
    }
    return list;
  }

  void _logout() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Déconnexion', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        content: const Text('Voulez-vous vraiment vous déconnecter ?', style: TextStyle(color: Color(0xFF94A3B8))),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Annuler', style: TextStyle(color: Color(0xFF64748B))),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFEF4444),
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              await ApiClient.logout();   // révoque aussi le refresh token côté backend
              if (!context.mounted) return;
              Navigator.pop(context);
              Navigator.pushReplacement(
                context,
                MaterialPageRoute(builder: (_) => const AuthScreen()),
              );
            },
            child: const Text('Se déconnecter'),
          ),
        ],
      ),
    );
  }

  void _openCourse(SubjectModel subject, LessonModel lesson) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => NotebookScreen(
          initialSubject: subject,
          initialLesson: lesson,
        ),
      ),
    ).then((_) => _loadData());
  }

  void _openNewSpaceDialog() {
    final controller = TextEditingController();
    String selectedColor = '#1E40AF';
    final colors = ['#1E40AF', '#DC2626', '#15803D', '#7C3AED', '#D97706', '#0D9488'];

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: const Text('Nouvel Espace de Travail', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Nom de la matière ou catégorie :', style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
              const SizedBox(height: 6),
              TextField(
                controller: controller,
                autofocus: true,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Ex: Mathématiques, Physique',
                  hintStyle: const TextStyle(color: Color(0xFF64748B)),
                  filled: true,
                  fillColor: const Color(0xFF0F172A),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 14),
              const Text('Couleur distinctive :', style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: colors.map((colHex) {
                  final isSelected = selectedColor == colHex;
                  final colorVal = Color(int.parse(colHex.replaceFirst('#', '0xFF')));
                  return GestureDetector(
                    onTap: () => setDialogState(() => selectedColor = colHex),
                    child: Container(
                      padding: const EdgeInsets.all(2),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: isSelected ? Colors.cyanAccent : Colors.transparent,
                          width: 2,
                        ),
                      ),
                      child: CircleAvatar(
                        radius: 12,
                        backgroundColor: colorVal,
                        child: isSelected ? const Icon(Icons.check, size: 12, color: Colors.white) : null,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Annuler', style: TextStyle(color: Color(0xFF64748B))),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                foregroundColor: Colors.white,
              ),
              onPressed: () async {
                final name = controller.text.trim();
                if (name.isEmpty) return;

                final created = await ApiClient.createSubject(name, selectedColor);

                setState(() {
                  _subjects.add(
                    created ?? SubjectModel(
                      id: 'subj-${DateTime.now().millisecondsSinceEpoch}',
                      name: name,
                      color: selectedColor,
                      lessons: [],
                    ),
                  );
                });
                if (context.mounted) {
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Espace "$name" créé avec succès.')),
                  );
                }
              },
              child: const Text('Créer l\'espace'),
            ),
          ],
        ),
      ),
    );
  }

  void _openNewCourseDialog([SubjectModel? preselectedSubject]) {
    final titleController = TextEditingController();
    SubjectModel? targetSubject = preselectedSubject ?? (_subjects.isNotEmpty ? _subjects.first : null);

    if (_subjects.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Veuillez d\'abord créer un espace de travail.')),
      );
      _openNewSpaceDialog();
      return;
    }

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: const Text('Nouveau Cours', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Titre du cours :', style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
              const SizedBox(height: 6),
              TextField(
                controller: titleController,
                autofocus: true,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Ex: Fonctions & Dérivées',
                  hintStyle: const TextStyle(color: Color(0xFF64748B)),
                  filled: true,
                  fillColor: const Color(0xFF0F172A),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 14),
              const Text('Espace de rattachement :', style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
              const SizedBox(height: 6),
              DropdownButtonFormField<SubjectModel>(
                initialValue: targetSubject,
                dropdownColor: const Color(0xFF1E293B),
                style: const TextStyle(color: Colors.white),
                items: _subjects.map((s) => DropdownMenuItem(value: s, child: Text(s.name, style: const TextStyle(color: Colors.white)))).toList(),
                onChanged: (val) {
                  if (val != null) setDialogState(() => targetSubject = val);
                },
                decoration: InputDecoration(
                  filled: true,
                  fillColor: const Color(0xFF0F172A),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Annuler', style: TextStyle(color: Color(0xFF64748B))),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                foregroundColor: Colors.white,
              ),
              onPressed: () async {
                final title = titleController.text.trim();
                if (title.isEmpty || targetSubject == null) return;

                final createdLesson = await ApiClient.createLesson(title, targetSubject!.id);

                final finalLesson = createdLesson ?? LessonModel(
                  id: 'les-${DateTime.now().millisecondsSinceEpoch}',
                  title: title,
                  updatedAt: DateTime.now().toIso8601String().split('T').first,
                );

                setState(() {
                  targetSubject!.lessons.insert(0, finalLesson);
                });
                if (context.mounted) {
                  Navigator.pop(context);
                  _openCourse(targetSubject!, finalLesson);
                }
              },
              child: const Text('Commencer à écrire'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final totalCoursesCount = _subjects.fold<int>(0, (sum, s) => sum + s.lessons.length);

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Dark Stitch Theme background
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.asset('assets/logo.png', width: 28, height: 28, fit: BoxFit.contain),
            ),
            const SizedBox(width: 10),
            const Text(
              'Notely',
              style: TextStyle(fontWeight: FontWeight.w900, color: Colors.white, fontSize: 20, letterSpacing: -0.5),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.create_new_folder_outlined, color: Color(0xFF94A3B8)),
            tooltip: 'Nouvel Espace',
            onPressed: _openNewSpaceDialog,
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: Color(0xFFEF4444)),
            tooltip: 'Se déconnecter',
            onPressed: _logout,
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFF818CF8)))
          : RefreshIndicator(
              onRefresh: _loadData,
              color: const Color(0xFF818CF8),
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Banner Stitch / InkAI Header
                  Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF1E1B4B), Color(0xFF312E81), Color(0xFF1E293B)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFF4338CA).withValues(alpha: 0.5)),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF4F46E5).withValues(alpha: 0.2),
                          blurRadius: 15,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: const Color(0xFF22C55E).withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(20),
                                border: Border.all(color: const Color(0xFF22C55E)),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  CircleAvatar(radius: 4, backgroundColor: Color(0xFF22C55E)),
                                  SizedBox(width: 6),
                                  Text(
                                    'OCR & IA Actif',
                                    style: TextStyle(fontSize: 11, color: Color(0xFF4ADE80), fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Espace d\'Apprentissage Manuscrit',
                          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Colors.white),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Numérisation vectorielle & révision automatisée par IA',
                          style: TextStyle(fontSize: 12, color: Color(0xFFC7D2FE)),
                        ),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            _buildStatChip('${_subjects.length}', 'Espaces (Matières)'),
                            const SizedBox(width: 10),
                            _buildStatChip('$totalCoursesCount', 'Cours Registrés'),
                          ],
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Barre de Recherche Stitch
                  TextField(
                    onChanged: (val) => setState(() => _searchQuery = val),
                    style: const TextStyle(color: Colors.white, fontSize: 14),
                    decoration: InputDecoration(
                      hintText: 'Rechercher un cours, une matière...',
                      hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 14),
                      prefixIcon: const Icon(Icons.search, color: Color(0xFF818CF8)),
                      suffixIcon: _searchQuery.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear, color: Color(0xFF64748B), size: 18),
                              onPressed: () => setState(() => _searchQuery = ''),
                            )
                          : null,
                      filled: true,
                      fillColor: const Color(0xFF1E293B),
                      contentPadding: const EdgeInsets.symmetric(vertical: 12),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFF334155)),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFF334155)),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFF818CF8)),
                      ),
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Horizontal Filter Chips (Matières / Espaces)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Espaces de Travail',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (_selectedSubjectId != null) ...[
                            IconButton(
                              icon: const Icon(Icons.edit, size: 16, color: Color(0xFF818CF8)),
                              tooltip: 'Modifier l'espace sélectionné',
                              onPressed: () {
                                final s = _subjects.firstWhere((item) => item.id == _selectedSubjectId);
                                _openEditSpaceDialog(s);
                              },
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete_outline, size: 16, color: Color(0xFFEF4444)),
                              tooltip: 'Supprimer l'espace sélectionné',
                              onPressed: () {
                                final s = _subjects.firstWhere((item) => item.id == _selectedSubjectId);
                                _confirmDeleteSpace(s);
                              },
                            ),
                          ],
                          TextButton.icon(
                            onPressed: _openNewSpaceDialog,
                            icon: const Icon(Icons.add_circle_outline, size: 16, color: Color(0xFF818CF8)),
                            label: const Text('Créer', style: TextStyle(color: Color(0xFF818CF8), fontWeight: FontWeight.bold, fontSize: 13)),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        // Chip "Tous"
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: ChoiceChip(
                            label: Text('Tous ($totalCoursesCount)'),
                            selected: _selectedSubjectId == null,
                            selectedColor: const Color(0xFF4F46E5),
                            backgroundColor: const Color(0xFF1E293B),
                            labelStyle: TextStyle(
                              color: _selectedSubjectId == null ? Colors.white : const Color(0xFF94A3B8),
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                            ),
                            side: BorderSide(
                              color: _selectedSubjectId == null ? const Color(0xFF6366F1) : const Color(0xFF334155),
                            ),
                            onSelected: (sel) {
                              if (sel) setState(() => _selectedSubjectId = null);
                            },
                          ),
                        ),
                        // Chips des matières
                        ..._subjects.map((subj) {
                          final isSel = _selectedSubjectId == subj.id;
                          final colorVal = Color(int.parse(subj.color.replaceFirst('#', '0xFF')));
                          return Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: ChoiceChip(
                              avatar: CircleAvatar(radius: 4, backgroundColor: colorVal),
                              label: Text('${subj.name} (${subj.lessons.length})'),
                              selected: isSel,
                              selectedColor: colorVal.withValues(alpha: 0.3),
                              backgroundColor: const Color(0xFF1E293B),
                              labelStyle: TextStyle(
                                color: isSel ? Colors.white : const Color(0xFF94A3B8),
                                fontWeight: isSel ? FontWeight.bold : FontWeight.normal,
                                fontSize: 12,
                              ),
                              side: BorderSide(
                                color: isSel ? colorVal : const Color(0xFF334155),
                              ),
                              onSelected: (sel) {
                                setState(() => _selectedSubjectId = sel ? subj.id : null);
                              },
                            ),
                          );
                        }),
                      ],
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Liste des Cours Filtrés
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        _selectedSubjectId == null
                            ? 'Tous les Cours'
                            : 'Cours dans "${_subjects.firstWhere((s) => s.id == _selectedSubjectId).name}"',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      Text(
                        '${_filteredCourses.length} cours',
                        style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),

                  if (_filteredCourses.isEmpty)
                    _buildEmptyState('Aucun cours trouvé', 'Créez un nouveau cours ou modifiez votre filtre de recherche.')
                  else
                    ..._filteredCourses.map((item) {
                      final SubjectModel subj = item['subject'];
                      final LessonModel les = item['lesson'];
                      final colorVal = Color(int.parse(subj.color.replaceFirst('#', '0xFF')));

                      return Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: const Color(0xFF334155)),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.2),
                              blurRadius: 6,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        ),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          leading: Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: colorVal.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: colorVal.withValues(alpha: 0.4)),
                            ),
                            child: Icon(Icons.description_outlined, color: colorVal, size: 22),
                          ),
                          title: Text(
                            les.title,
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white),
                          ),
                          subtitle: Padding(
                            padding: const EdgeInsets.only(top: 4),
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: colorVal.withValues(alpha: 0.2),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    subj.name,
                                    style: TextStyle(fontSize: 10, color: colorVal, fontWeight: FontWeight.bold),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  'Modifié le ${les.updatedAt}',
                                  style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                                ),
                              ],
                            ),
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              PopupMenuButton<String>(
                                icon: const Icon(Icons.more_vert, size: 20, color: Color(0xFF94A3B8)),
                                color: const Color(0xFF1E293B),
                                tooltip: 'Options du cours',
                                onSelected: (val) {
                                  if (val == 'rename') {
                                    _openRenameCourseDialog(subj, les);
                                  } else if (val == 'delete') {
                                    _confirmDeleteCourse(subj, les);
                                  }
                                },
                                itemBuilder: (context) => const [
                                  PopupMenuItem(
                                    value: 'rename',
                                    child: Row(children: [
                                      Icon(Icons.edit, size: 16, color: Colors.blueAccent),
                                      SizedBox(width: 8),
                                      Text('Renommer', style: TextStyle(color: Colors.white, fontSize: 13)),
                                    ]),
                                  ),
                                  PopupMenuItem(
                                    value: 'delete',
                                    child: Row(children: [
                                      Icon(Icons.delete_outline, size: 16, color: Colors.redAccent),
                                      SizedBox(width: 8),
                                      Text('Supprimer', style: TextStyle(color: Colors.redAccent, fontSize: 13)),
                                    ]),
                                  ),
                                ],
                              ),
                              const Icon(Icons.arrow_forward_ios, size: 14, color: Color(0xFF64748B)),
                            ],
                          ),
                          onTap: () => _openCourse(subj, les),
                        ),
                      );
                    }),
                ],
              ),
            ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF4F46E5),
        foregroundColor: Colors.white,
        icon: const Icon(Icons.edit_note),
        label: const Text('Nouveau Cours', style: TextStyle(fontWeight: FontWeight.bold)),
        onPressed: () => _openNewCourseDialog(_selectedSubjectId != null ? _subjects.firstWhere((s) => s.id == _selectedSubjectId) : null),
      ),
    );
  }

  Widget _buildStatChip(String count, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(count, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF818CF8))),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFFE2E8F0), fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  Widget _buildEmptyState(String title, String desc) {
    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        children: [
          const Icon(Icons.menu_book, size: 36, color: Color(0xFF64748B)),
          const SizedBox(height: 10),
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white)),
          const SizedBox(height: 4),
          Text(desc, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
        ],
      ),
    );
  }

  // ── Méthodes CRUD Espaces & Cours (Parité Web/Mobile) ──────────────────────

  void _openEditSpaceDialog(SubjectModel subject) {
    final controller = TextEditingController(text: subject.name);
    String selectedColor = subject.color;
    final colors = ['#1E40AF', '#DC2626', '#15803D', '#7C3AED', '#D97706', '#0D9488'];

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: const Text('Modifier l'Espace', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Nom de la matière ou catégorie :', style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
              const SizedBox(height: 6),
              TextField(
                controller: controller,
                autofocus: true,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: const Color(0xFF0F172A),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 14),
              const Text('Couleur distinctive :', style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: colors.map((colHex) {
                  final isSelected = selectedColor == colHex;
                  final colorVal = Color(int.parse(colHex.replaceFirst('#', '0xFF')));
                  return GestureDetector(
                    onTap: () => setDialogState(() => selectedColor = colHex),
                    child: Container(
                      padding: const EdgeInsets.all(2),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: isSelected ? Colors.cyanAccent : Colors.transparent,
                          width: 2,
                        ),
                      ),
                      child: CircleAvatar(
                        radius: 12,
                        backgroundColor: colorVal,
                        child: isSelected ? const Icon(Icons.check, size: 12, color: Colors.white) : null,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Annuler', style: TextStyle(color: Color(0xFF64748B))),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                foregroundColor: Colors.white,
              ),
              onPressed: () async {
                final newName = controller.text.trim();
                if (newName.isEmpty) return;
                final ok = await ApiClient.updateSubject(subject.id, newName, selectedColor);
                if (context.mounted) {
                  Navigator.pop(context);
                  if (ok) {
                    _loadData();
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Espace "$newName" modifié avec succès.')),
                    );
                  }
                }
              },
              child: const Text('Enregistrer'),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmDeleteSpace(SubjectModel subject) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Supprimer l'Espace', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        content: Text(
          'Voulez-vous vraiment supprimer l'espace "${subject.name}" et tous les cours qu'il contient ? Cette action est irréversible.',
          style: const TextStyle(color: Color(0xFF94A3B8)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Annuler', style: TextStyle(color: Color(0xFF64748B))),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFEF4444),
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              final ok = await ApiClient.deleteSubject(subject.id);
              if (context.mounted) {
                Navigator.pop(context);
                if (_selectedSubjectId == subject.id) {
                  setState(() => _selectedSubjectId = null);
                }
                _loadData();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Espace "${subject.name}" supprimé.')),
                );
              }
            },
            child: const Text('Supprimer définitivement'),
          ),
        ],
      ),
    );
  }

  void _openRenameCourseDialog(SubjectModel subject, LessonModel lesson) {
    final controller = TextEditingController(text: lesson.title);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Renommer le Cours', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Nouveau titre :', style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
            const SizedBox(height: 6),
            TextField(
              controller: controller,
              autofocus: true,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                filled: true,
                fillColor: const Color(0xFF0F172A),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Annuler', style: TextStyle(color: Color(0xFF64748B))),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF6366F1),
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              final newTitle = controller.text.trim();
              if (newTitle.isEmpty) return;
              final ok = await ApiClient.renameLesson(subject.id, lesson.id, newTitle);
              if (context.mounted) {
                Navigator.pop(context);
                if (ok) {
                  _loadData();
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Cours renommé en "$newTitle".')),
                  );
                }
              }
            },
            child: const Text('Enregistrer'),
          ),
        ],
      ),
    );
  }

  void _confirmDeleteCourse(SubjectModel subject, LessonModel lesson) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Supprimer le Cours', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        content: Text(
          'Voulez-vous vraiment supprimer le cours "${lesson.title}" ? Tous les tracés et notes associées seront effacés.',
          style: const TextStyle(color: Color(0xFF94A3B8)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Annuler', style: TextStyle(color: Color(0xFF64748B))),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFEF4444),
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              final ok = await ApiClient.deleteLesson(subject.id, lesson.id);
              if (context.mounted) {
                Navigator.pop(context);
                _loadData();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Cours "${lesson.title}" supprimé.')),
                );
              }
            },
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
  }

}
