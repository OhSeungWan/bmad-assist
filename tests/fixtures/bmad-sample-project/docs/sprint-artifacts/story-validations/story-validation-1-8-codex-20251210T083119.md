### Ruthless Story Validation 1.8

### INVEST Violations
- I (Independence) [severity 6]: Zadanie zależy od wcześniejszych story 1.2-1.5 (podział testów per story) oraz stanu obecnych testów (294 testy w test_config.py, linie 16-18), bez planu jak poradzić sobie z równoległymi zmianami lub blokadami w tych modułach.
- N (Negotiable) [severity 4]: Wymagania są w dużej mierze sztywne (konkretny podział plików, brak zmian logiki), brak przestrzeni na kompromisy jeśli pojawią się konflikty strukturalne w testach.
- S (Small) [severity 7]: 2 SP jest skrajnie niedoszacowane względem zakresu: rozbicie 3003 linii na 4 pliki, wyciąganie fixtures, dostosowanie importów, walidacje (linia 16, 94-111) to praca na co najmniej kilka dni z ryzykiem regresji.
- T (Testable) [severity 5]: Brak jednoznacznych metryk dla „czas wykonania nie wzrósł znacząco (±10%)” (linia 60) i brak planu porównania baseline; brak kryteriów akceptacji dla aktualizacji ścieżek importów po rozbiciu plików.

### Acceptance Criteria Issues
- AC1 (linia 32-43): Nie opisuje migracji referencji/importów ani mechanizmu weryfikacji, że żaden plik nie przekracza 500 linii po refaktorze (brak checków w zadaniach/AC, linia 109 wspomina, ale bez metody).
- AC2 (linia 45-52): Brak wskazania, które fixtures są „shared” oraz kryterium braku duplikacji – grozi niespójnością fixtures lub ukrytym rozbiciem setupu.
- AC3/AC4 (linia 54-70): Wymagają utrzymania 294 testów i coverage ≥95%, ale brak baseline i listy krytycznych ścieżek; „brak nowych warnings” i „czas ±10%” są nieoperacjonalne bez metryki startowej.
- AC5 (linia 72-78): Oznaczone jako opcjonalne, ale brak kryterium, kiedy należy je wykonać (próg 871 linii już przekroczony) – ryzyko, że zostanie pominięte mimo krytycznej wielkości pliku.

### Hidden Risks & Dependencies
- Ukryte zależności na treści test_config.py: brak analizy wpływu na test_config_generator.py, test_cli.py i importy w conftest.py (linia 117-146). 
- Brak planu aktualizacji tooling (pytest.ini, ruff/mypy) po przenosinach – może wymagać zmian ścieżek i markerów.
- Potencjalne konflikty z bieżącymi zmianami w branchu (rozbijanie dużego pliku testów często koliduje z innymi PR).
- Ryzyko utraty fixtures (reset_config_singleton, sample configs) jeśli nie zostaną przeniesione 1:1 (linia 181-235), brak weryfikacji poprawności w AC.

### Estimation Reality-Check
- 2 SP jest nierealne: przeniesienie 3003 linii + utrzymanie 294 testów + ewentualny podział 871 linii w test_cli.py to zadanie złożone (refaktor bez zmiany logiki, walidacja linii, mypy, ruff, coverage). Realistycznie 5-8 SP.

### Technical Alignment
- Struktura docelowa (linia 131-147) jest zgodna z architecture.md (podział core/fixtures), ale brak explicit powiązania z wymogiem PEP8/typów (project_context) i brakuje checku, że nowe pliki zachowają coverage ≥95% (project standards).
- Brak odniesienia do architektonicznych wzorców atomowych zapisów/testów (architecture.md) oraz brak wzmianki o utrzymaniu Google-style docstrings/typing w nowych modułach testowych.
- Nie uwzględniono wymogu BDD dla AC w nowych plikach (project_standards), ani jak zapewnić >95% coverage po podziale.

### Final Score (1-10)
3

### Verdict: READY | MAJOR REWORK | REJECT
MAJOR REWORK
