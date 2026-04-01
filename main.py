# pip install canvasapi
from canvasapi import Canvas

# --- CONFIGURATIE ---
API_URL = "https://canvas.hu.nl"

# Haal eigen API key op uit: https://canvas.hu.nl/profile/settings -> Nieuwe toegangstoken
API_KEY = ""

# Kun je zelf halen uit de url
COURSE_ID = 10000
# Kun je zelf halen uit de url van assignment
ASSIGNMENT_ID = 100000
# Dit is voor klas C
TARGET_SECTION_NAME = ""

# DRY_RUN
DRY_RUN = False

canvas = Canvas(API_URL, API_KEY)
course = canvas.get_course(COURSE_ID)
assignment = course.get_assignment(ASSIGNMENT_ID)

sections = course.get_sections()
target_section = next((s for s in sections if s.name == TARGET_SECTION_NAME), None)

if not target_section:
    raise Exception(f"Sectie '{TARGET_SECTION_NAME}' niet gevonden in cursus {COURSE_ID}.")

# Kun je ook handmatig invullen als je het id weet
TARGET_SECTION_ID = target_section.id


def get_dynamic_rubric_assessment(assignment_obj):
    """Zoekt automatisch naar de 'geen' ratings in de rubriek."""
    rubric = getattr(assignment_obj, 'rubric', [])
    assessment = {}

    for criterion in rubric:
        criterion_id = criterion['id']
        # Zoek de rating die 'geen' bevat (hoofdletterongevoelig)
        target_rating = next((r for r in criterion['ratings'] if "geen" in r['description'].lower()), None)

        if target_rating:
            assessment[criterion_id] = {
                'rating_id': target_rating['id'],
                'points': target_rating['points']
            }
            print(
                f"Rubriek gevonden: Criterium '{criterion['description']}' -> Rating '{target_rating['description']}' ({target_rating['points']} pnt)")

    return assessment


def auto_grade_dynamic():
    # 1. Haal de rubriek instellingen dynamisch op
    rubric_assessment = get_dynamic_rubric_assessment(assignment)

    if not rubric_assessment:
        print("❌ Fout: Geen rubriek-items gevonden met de tekst 'geen'.")
        return

    print(f"Lidmaatschappen ophalen voor sectie: {TARGET_SECTION_NAME}...")
    section_users = target_section.get_enrollments(type=['StudentEnrollment'])
    target_user_ids = {enrollment.user_id for enrollment in section_users}

    # 3. Haal alle submissions op inclusief user data voor de naam
    print(f"Inzendingen controleren voor {len(target_user_ids)} studenten...")
    submissions = assignment.get_submissions(include=['user'])

    count = 0
    for sub in submissions:
        # Filter op jouw sectie
        if sub.user_id not in target_user_ids:
            continue

        # Filter op niet ingeleverd en nog geen cijfer
        if sub.workflow_state in ['unsubmitted', 'missing'] and sub.score is None:
            try:
                student_name = sub.user.get('name', sub.user_id)

                # 3. Pas de beoordeling toe, comment wordt ook toegepast
                if not DRY_RUN:
                    sub.edit(
                        rubric_assessment=rubric_assessment,
                        submission={'posted_grade': '0'},
                        comment={'text_comment': 'Automatisch ingevuld: geen inlevering.'}
                    )
                print(f"✅ Student {student_name} ({sub.user_id}) bijgewerkt.")
                count += 1
            except Exception as e:
                print(f"❌ Fout bij student {sub.user_id}: {e}")

    print(f"\nKlaar! Totaal {count} studenten verwerkt.")


if __name__ == "__main__":
    auto_grade_dynamic()