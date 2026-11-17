"""Small fixed document-label catalog; never translates human-authored evidence."""
from datetime import date
import re

_KEYS = ('Summary','Experience','Volunteering','Projects','Education','Certifications',
         'Publications','Skills','Languages','References','Additional','Present','Resume',
         'Cover letter','Group','Self-described level','Credential','Relationship','Link','Email','Phone')
_ROWS = {
 'en': ('English - original ISO dates', 'Summary|Experience|Volunteering|Projects|Education|Certifications|Publications|Skills|Languages|References|Additional|Present|Resume|Cover letter|Group|Self-described level|Credential|Relationship|Link|Email|Phone',
        'January|February|March|April|May|June|July|August|September|October|November|December',
        'Dear hiring team,', 'I am applying for the {title} role at {company}.', 'Selected examples from my reviewed record:'),
 'de': ('Deutsch', 'Profil|Berufserfahrung|Ehrenamt|Projekte|Ausbildung|Zertifizierungen|Publikationen|Kenntnisse|Sprachen|Referenzen|Weitere Angaben|Heute|Lebenslauf|Anschreiben|Gruppe|Selbsteinschätzung|Nachweis|Beziehung|Link|E-Mail|Telefon',
        'Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember',
        'Sehr geehrtes Recruiting-Team,', 'Hiermit bewerbe ich mich auf die Position {title} bei {company}.', 'Ausgewählte Beispiele aus meinen geprüften Angaben:'),
 'es': ('Español', 'Perfil|Experiencia|Voluntariado|Proyectos|Formación|Certificaciones|Publicaciones|Competencias|Idiomas|Referencias|Información adicional|Actualidad|Currículum|Carta de presentación|Grupo|Nivel autodeclarado|Credencial|Relación|Enlace|Correo electrónico|Teléfono',
        'enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre',
        'Estimado equipo de selección:', 'Presento mi candidatura al puesto de {title} en {company}.', 'Ejemplos seleccionados de mis datos revisados:'),
 'fr': ('Français', 'Profil|Expérience|Bénévolat|Projets|Formation|Certifications|Publications|Compétences|Langues|Références|Informations complémentaires|Aujourd’hui|CV|Lettre de motivation|Groupe|Niveau autodéclaré|Identifiant|Relation|Lien|E-mail|Téléphone',
        'janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre',
        'Madame, Monsieur,', 'Je présente ma candidature au poste de {title} chez {company}.', 'Exemples sélectionnés parmi mes informations vérifiées :'),
 'it': ('Italiano', 'Profilo|Esperienza|Volontariato|Progetti|Formazione|Certificazioni|Pubblicazioni|Competenze|Lingue|Referenze|Altre informazioni|Oggi|Curriculum|Lettera di presentazione|Gruppo|Livello autodichiarato|Credenziale|Relazione|Link|E-mail|Telefono',
        'gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre',
        'Gentile team di selezione,', 'Presento la mia candidatura per il ruolo di {title} presso {company}.', 'Esempi selezionati dalle mie informazioni verificate:'),
 'pt-BR': ('Português (Brasil)', 'Perfil|Experiência|Voluntariado|Projetos|Formação|Certificações|Publicações|Competências|Idiomas|Referências|Informações adicionais|Atual|Currículo|Carta de apresentação|Grupo|Nível autodeclarado|Credencial|Relação|Link|E-mail|Telefone',
        'janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro',
        'Prezada equipe de recrutamento,', 'Apresento minha candidatura à vaga de {title} na empresa {company}.', 'Exemplos selecionados dos meus dados revisados:'),
 'nl': ('Nederlands', 'Profiel|Werkervaring|Vrijwilligerswerk|Projecten|Opleiding|Certificeringen|Publicaties|Vaardigheden|Talen|Referenties|Overige informatie|Heden|CV|Sollicitatiebrief|Groep|Zelfbeschreven niveau|Referentienummer|Relatie|Link|E-mail|Telefoon',
        'januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december',
        'Geacht wervingsteam,', 'Hierbij solliciteer ik naar de functie {title} bij {company}.', 'Geselecteerde voorbeelden uit mijn gecontroleerde gegevens:'),
}
_ROWS['en-GB'] = ('English (UK) - named months', *_ROWS['en'][1:])
_ROWS['en-US'] = ('English (US) - named months', *_ROWS['en'][1:])


def checked_locale(locale):
    if not isinstance(locale, str) or locale not in _ROWS:
        raise ValueError('Choose a supported document language')
    return locale


def options():
    return [{'id': code, 'label': row[0]} for code, row in _ROWS.items()]


def label(key, locale='en'):
    row = _ROWS[checked_locale(locale)]
    return dict(zip(_KEYS, row[1].split('|'), strict=True))[key]


def month(value, locale='en'):
    checked_locale(locale)
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])', value):
        raise ValueError('Document month must be YYYY-MM')
    date(int(value[:4]), int(value[5:]), 1)
    if locale == 'en':
        return value
    name = _ROWS[locale][2].split('|')[int(value[5:])-1]
    return name + ' ' + value[:4]


def letter_labels(context, locale='en'):
    row = _ROWS[checked_locale(locale)]
    return row[3], row[4].format(title=context['title'], company=context['company']), row[5]
