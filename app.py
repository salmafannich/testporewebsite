from flask import Flask, logging, make_response, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os
from openpyxl import load_workbook

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Assurez-vous que ceci est défini avant d'utiliser les sessions

# Database setup
def init_sqlite_db():
    conn = sqlite3.connect('users.db')
    print("Opened database successfully")
    conn.execute('CREATE TABLE IF NOT EXISTS users (name TEXT, email TEXT, password TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS history (action TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
    print("Tables created successfully")
    conn.close()

init_sqlite_db()

@app.route('/history', methods=['GET', 'POST'])
def history():
    con = sqlite3.connect('users.db')
    cur = con.cursor()

    if request.method == 'POST':
        # Récupérer la date soumise par le formulaire
        date_filter = request.form.get('date_filter')
        # Requête pour filtrer par date
        cur.execute("SELECT * FROM history WHERE DATE(timestamp) = ?", (date_filter,))
    else:
        # Requête par défaut pour récupérer toutes les actions
        cur.execute("SELECT * FROM history ORDER BY timestamp DESC")

    actions = cur.fetchall()
    con.close()
    return render_template('history.html', actions=actions)

def log_action(action):
    con = sqlite3.connect('users.db')
    cur = con.cursor()
    cur.execute("INSERT INTO history (action) VALUES (?)", (action,))
    con.commit()
    con.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    con = None
    if request.method == 'POST':
        try:
            name = request.form['name']
            password = request.form['password']

            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            con = sqlite3.connect('users.db')
            cur = con.cursor()
            cur.execute("INSERT INTO users (name, password) VALUES (?, ?)", (name, hashed_password))
            con.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            if con:
                con.rollback()
            flash(f"Error occurred: {str(e)}", "danger")
        
        finally:
            if con:
                con.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        con = sqlite3.connect('users.db')
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE name = ?", (name,))
        user = cur.fetchone()

        if user and check_password_hash(user[2], password):  # Index 2 corresponds to the password column
            session['user_id'] = user[0]
            session['name'] = user[0]  # Assurez-vous que 'name' est correctement mis dans la session
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Login failed. Check your name and password.", "danger")

        con.close()

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')
import pandas as pd

@app.route('/view_epi', methods=['GET', 'POST'])
def view_epi():
    epi_excel_file = 'data of pore app\suivi de remise des EPI Finale.xlsx'  # Assurez-vous que ce chemin est correct
    df = pd.read_excel(epi_excel_file, engine='openpyxl')

    # Liste des colonnes de date
    date_columns = ['D EMBAUCHE', 'Date récharge EPI', 'Casque: date de remise', 'Chaussures: date de remise',
                    'Gants: date de remise', 'Gilet fluoreçant: date de remise', 'Combinaison imperméable: date de remise',
                    'Lunettes (Anti-poussière): date de remise', 'Bote de sécurité: date de remise',
                    'Gilet de sauvetage: date de remise', 'Autre: date de remise']

    # Convertir les colonnes de date en datetime et formater
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: '' if pd.isna(x) else x.strftime('%d/%m/%Y'))

    columns = df.columns.tolist()
    data = df.to_dict(orient='records')

    # Recherche
    if request.method == 'POST':
        search_criterion = request.form.get('search_criterion')
        search_value = request.form.get('search_value', '').strip()
        if search_criterion and search_value:
            data = [row for row in data if search_value.lower() in str(row.get(search_criterion, '')).lower()]

    # Pagination
    page = int(request.args.get('page', 1))  # Numéro de page (défaut à 1)
    per_page = 10  # Nombre de lignes par page
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_data = data[start:end]
    total_pages = (total + per_page - 1) // per_page  # Calcul du nombre total de pages

    return render_template(
        'view_epi.html',
        data=paginated_data,
        columns=columns,
        page=page,
        total_pages=total_pages,
        max=max,
        min=min
    )



@app.route('/import_epi', methods=['GET', 'POST'])
def import_epi():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            # Liste des colonnes de date
            date_columns = [
                'D EMBAUCHE', 'Date récharge EPI', 'Casque: date de remise', 'Chaussures: date de remise',
                'Gants: date de remise', 'Gilet fluoreçant: date de remise', 'Combinaison imperméable: date de remise',
                'Lunettes (Anti-poussière ): date de remise', 'Bote de sécurité: date de remise',
                'Gilet de sauvetage: date de remise', 'Autre: date de remise'
            ]

            # Déterminer le moteur en fonction de l'extension du fichier
            if file.filename.endswith('.xlsx'):
                engine = 'openpyxl'
            elif file.filename.endswith('.xls'):
                engine = 'xlrd'
            
            # Lire le nouveau fichier Excel
            df_new = pd.read_excel(file, engine=engine)
            # Lire le fichier Excel existant
            df_existing = pd.read_excel('data of pore app/suivi de remise des EPI Finale.xlsx', engine='openpyxl')

            # Vérifier si les colonnes correspondent
            if set(df_new.columns) == set(df_existing.columns):
                # Convertir les colonnes de date en datetime
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_datetime(df_new[col], errors='coerce', dayfirst=True)
                    if col in df_existing.columns:
                        df_existing[col] = pd.to_datetime(df_existing[col], errors='coerce', dayfirst=True)

                # Remplacer les dates NaT par des valeurs vides (ou une valeur par défaut si nécessaire)
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = df_new[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y') if isinstance(x, pd.Timestamp) else '')
                    if col in df_existing.columns:
                        df_existing[col] = df_existing[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y') if isinstance(x, pd.Timestamp) else '')

                # Combiner les DataFrames et supprimer les doublons
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates().reset_index(drop=True)
                # Enregistrer le fichier Excel combiné
                df_combined.to_excel('data of pore app/suivi de remise des EPI Finale.xlsx', index=False, engine='openpyxl')
                log_action("Importation nouveau epis")
                flash("Fichier importé et fusionné avec succès !", "success")
            else:
                flash("Les colonnes du fichier importé ne correspondent pas au tableau existant.", "danger")
        else:
            flash("Veuillez télécharger un fichier Excel valide (.xlsx ou .xls).", "danger")

        return redirect(url_for('view_epi'))
    
    return render_template('import_epi.html')


@app.route('/view_epi1')
def view_epi1():
    df = pd.read_excel('data of pore app/suivi de remise des EPI 1.xlsx')
    data = df.to_dict(orient='records')
    columns = df.columns.tolist()
    return render_template('view_epi1.html', data=data, columns=columns)
@app.route('/add_epi', methods=['GET', 'POST'])
def add_epi():
    if request.method == 'POST':
        form_data = {
            'Affectation': request.form.get('affectation', None),
            'MAT': request.form.get('mat', None),
            'Nom et Prénom': request.form.get('nom_prenom', None),
            'Fonction': request.form.get('fonction', None),
            'CIN': request.form.get('cin', None),
            'Date d\'embauche': request.form.get('date_embauche', None),
            'Date récharge EPI': request.form.get('date_recharge_epi', None),
            'SITE': request.form.get('site', None),
            'Casque: Nombre': request.form.get('casque_nombre', None),
            'Casque: Taille/type': request.form.get('casque_taille_type', None),
            'Casque: date de remise': request.form.get('casque_date_remise', None),
            'Chaussures: Nombre': request.form.get('chaussures_nombre', None),
            'Chaussures: Taille/type': request.form.get('chaussures_taille_type', None),
            'Chaussures: date de remise': request.form.get('chaussures_date_remise', None),
            'Gants: Nombre': request.form.get('gants_nombre', None),
            'Gants: Taille/type': request.form.get('gants_taille_type', None),
            'Gants: date de remise': request.form.get('gants_date_remise', None),
            'Gilet fluoreçant: Nombre': request.form.get('gilet_fluorescent_nombre', None),
            'Gilet fluoreçant: Taille/type': request.form.get('gilet_fluorescent_taille_type', None),
            'Gilet fluoreçant: date de remise': request.form.get('gilet_fluorescent_date_remise', None),
            'Combinaison imperméable: Nombre': request.form.get('combinaison_nombre', None),
            'Combinaison imperméable: Taille/type': request.form.get('combinaison_taille_type', None),
            'Combinaison imperméable: date de remise': request.form.get('combinaison_date_remise', None),
            'Lunettes (Anti-poussière ): Nombre': request.form.get('lunettes_nombre', None),
            'Lunettes (Anti-poussière ): Taille/type': request.form.get('lunettes_taille_type', None),
            'Lunettes (Anti-poussière ): date de remise': request.form.get('lunettes_date_remise', None),
            'Bote de sécurité: Nombre': request.form.get('bottes_nombre', None),
            'Bote de sécurité: Taille/type': request.form.get('bottes_taille_type', None),
            'Bote de sécurité: date de remise': request.form.get('bottes_date_remise', None),
            'Gilet de sauvetage: Nombre': request.form.get('gilet_sauvetage_nombre', None),
            'Gilet de sauvetage: Taille/type': request.form.get('gilet_sauvetage_taille_type', None),
            'Gilet de sauvetage: date de remise': request.form.get('gilet_sauvetage_date_remise', None),
            'Autre: Nombre': request.form.get('autre_nombre', None),
            'Autre: Taille/type': request.form.get('autre_taille_type', None),
            'Autre: date de remise': request.form.get('autre_date_remise', None)
        }

        try:
            excel_file_path = r'data of pore app\suivi de remise des EPI Finale.xlsx'

            # Charger le fichier Excel existant avec openpyxl
            wb = load_workbook(excel_file_path)

            # Sélectionner la première feuille de calcul
            sheet = wb.active

            # Ajouter les données du formulaire à la fin de la feuille de calcul
            row = [form_data['Affectation'], form_data['MAT'], form_data['Nom et Prénom'],
                   form_data['Fonction'], form_data['CIN'], form_data['Date d\'embauche'],
                   form_data['Date récharge EPI'], form_data['SITE'], form_data['Casque: Nombre'],
                   form_data['Casque: Taille/type'], form_data['Casque: date de remise'],
                   form_data['Chaussures: Nombre'], form_data['Chaussures: Taille/type'],
                   form_data['Chaussures: date de remise'], form_data['Gants: Nombre'],
                   form_data['Gants: Taille/type'], form_data['Gants: date de remise'],
                   form_data['Gilet fluoreçant: Nombre'], form_data['Gilet fluoreçant: Taille/type'],
                   form_data['Gilet fluoreçant: date de remise'], form_data['Combinaison imperméable: Nombre'],
                   form_data['Combinaison imperméable: Taille/type'], form_data['Combinaison imperméable: date de remise'],
                   form_data['Lunettes (Anti-poussière ): Nombre'], form_data['Lunettes (Anti-poussière ): Taille/type'],
                   form_data['Lunettes (Anti-poussière ): date de remise'], form_data['Bote de sécurité: Nombre'],
                   form_data['Bote de sécurité: Taille/type'], form_data['Bote de sécurité: date de remise'],
                   form_data['Gilet de sauvetage: Nombre'], form_data['Gilet de sauvetage: Taille/type'],
                   form_data['Gilet de sauvetage: date de remise'], form_data['Autre: Nombre'],
                   form_data['Autre: Taille/type'], form_data['Autre: date de remise']]
            
            sheet.append(row)

            # Sauvegarder le fichier Excel
            wb.save(excel_file_path)
            log_action("Ajout Nouveau Epi")
            flash("Nouvel enregistrement ajouté avec succès !", "success")
            return redirect(url_for('view_epi'))
        except FileNotFoundError:
            flash("Fichier non trouvé : data of pore app\\suivi de remise des EPI Finale.xlsx", "danger")
            return redirect(url_for('add_epi'))
        except Exception as e:
            flash(f"Erreur : {str(e)}", "danger")
            return redirect(url_for('add_epi'))

    return render_template('add_epi.html')

@app.route('/add_epi1', methods=['GET', 'POST'])
def add_epi1():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        date = request.form['date']
        nom_prenom = request.form['nom_prenom']
        fonction = request.form['fonction']
        section = request.form['section']
        tomp = request.form['tomp']

        try:
            # Charger le fichier Excel existant
            df = pd.read_excel('data of pore app/suivi de remise des EPI 1.xlsx', engine='openpyxl')
        except FileNotFoundError:
            # Créer un nouveau DataFrame si le fichier n'existe pas encore
            df = pd.DataFrame(columns=['DATE', 'NOM ET PRENOM', 'FONCTION', 'SECTION', 'TOMP'])

        # Créer un nouveau DataFrame pour le nouvel enregistrement
        new_record = pd.DataFrame({'DATE': [date], 'NOM ET PRENOM': [nom_prenom], 
                                   'FONCTION': [fonction], 'SECTION': [section], 
                                   'TOMP': [tomp]})

        # Concaténer le nouveau DataFrame avec le DataFrame existant
        df = pd.concat([df, new_record], ignore_index=True)
        
        # Réorganiser les colonnes pour garantir l'ordre correct
        df = df[['DATE', 'NOM ET PRENOM', 'FONCTION', 'SECTION', 'TOMP']]

        # Écrire le DataFrame mis à jour dans le fichier Excel
        df.to_excel('data of pore app/suivi de remise des EPI 1.xlsx', index=False, engine='openpyxl')

        flash("New record added successfully!", "success")
        return redirect(url_for('view_epi1'))
    
    return render_template('add_epi1.html')



@app.route('/update_epi/<int:row_id>', methods=['GET', 'POST'])
def update_epi(row_id):
    # Charger le fichier Excel dans un DataFrame
    df = pd.read_excel('data of pore app/suivi de remise des EPI Finale.xlsx', engine='openpyxl')

    if request.method == 'POST':
        # Mettre à jour l'enregistrement avec les données du formulaire
        df.at[row_id, 'AFFECTATION'] = request.form['affectation']
        df.at[row_id, 'MAT'] = request.form['mat']
        df.at[row_id, 'NOM ET PRENOM'] = request.form['nom_prenom']
        df.at[row_id, 'FONCTION'] = request.form['fonction']
        df.at[row_id, 'CIN'] = request.form['cin']
        df.at[row_id, 'D EMBAUCHE'] = request.form['d_embauche']
        df.at[row_id, 'Date récharge EPI'] = request.form['date_recharge_epi']
        df.at[row_id, 'SITE'] = request.form['site']
        df.at[row_id, 'Casque: Nombre'] = request.form['casque_nombre']
        df.at[row_id, 'Casque: Taille/type'] = request.form['casque_taille_type']
        df.at[row_id, 'Casque: date de remise'] = request.form['casque_date_remise']
        df.at[row_id, 'Chaussures: Nombre'] = request.form['chaussures_nombre']
        df.at[row_id, 'Chaussures: Taille/type'] = request.form['chaussures_taille_type']
        df.at[row_id, 'Chaussures: date de remise'] = request.form['chaussures_date_remise']
        df.at[row_id, 'Gants: Nombre'] = request.form['gants_nombre']
        df.at[row_id, 'Gants: Taille/type'] = request.form['gants_taille_type']
        df.at[row_id, 'Gants: date de remise'] = request.form['gants_date_remise']
        df.at[row_id, 'Gilet fluoreçant: Nombre'] = request.form['gilet_fluorescent_nombre']
        df.at[row_id, 'Gilet fluoreçant: Taille/type'] = request.form['gilet_fluorescent_taille_type']
        df.at[row_id, 'Gilet fluoreçant: date de remise'] = request.form['gilet_fluorescent_date_remise']
        df.at[row_id, 'Combinaison imperméable: Nombre'] = request.form['combinaison_impermeable_nombre']
        df.at[row_id, 'Combinaison imperméable: Taille/type'] = request.form['combinaison_impermeable_taille_type']
        df.at[row_id, 'Combinaison imperméable: date de remise'] = request.form['combinaison_impermeable_date_remise']
        df.at[row_id, 'Lunettes (Anti-poussière ): Nombre'] = request.form['lunettes_nombre']
        df.at[row_id, 'Lunettes (Anti-poussière ): Taille/type'] = request.form['lunettes_taille_type']
        df.at[row_id, 'Lunettes (Anti-poussière ): date de remise'] = request.form['lunettes_date_remise']
        df.at[row_id, 'Bote de sécurité: Nombre'] = request.form['bote_securite_nombre']
        df.at[row_id, 'Bote de sécurité: Taille/type'] = request.form['bote_securite_taille_type']
        df.at[row_id, 'Bote de sécurité: date de remise'] = request.form['bote_securite_date_remise']
        df.at[row_id, 'Gilet de sauvetage: Nombre'] = request.form['gilet_sauvetage_nombre']
        df.at[row_id, 'Gilet de sauvetage: Taille/type'] = request.form['gilet_sauvetage_taille_type']
        df.at[row_id, 'Gilet de sauvetage: date de remise'] = request.form['gilet_sauvetage_date_remise']
        df.at[row_id, 'Autre: Nombre'] = request.form['autre_nombre']
        df.at[row_id, 'Autre: Taille/type'] = request.form['autre_taille_type']
        df.at[row_id, 'Autre: date de remise'] = request.form['autre_date_remise']

        # Enregistrer le DataFrame mis à jour dans le fichier Excel
        df.to_excel('data of pore app/suivi de remise des EPI Finale.xlsx', index=False, engine='openpyxl')
        log_action("Mise à jour d'un Epi")
        flash("Record updated successfully!", "success")
        return redirect(url_for('view_epi'))

    # Récupérer l'enregistrement à mettre à jour basé sur row_id
    record = df.iloc[row_id].to_dict()

    return render_template('update_epi.html', record=record)


@app.route('/update_epi1/<int:row_id>', methods=['GET', 'POST'])
def update_epi1(row_id):
    # Load the Excel file into a DataFrame
    df = pd.read_excel('data of pore app/suivi de remise des EPI 1.xlsx', engine='openpyxl')

    if request.method == 'POST':
        # Update the record with form data
        df.at[row_id, 'DATE'] = request.form['date']
        df.at[row_id, 'NOM ET PRENOM'] = request.form['nom_prenom']
        df.at[row_id, 'FONCTION'] = request.form['fonction']
        df.at[row_id, 'SECTION'] = request.form['section']
        df.at[row_id, 'TOMP'] = request.form['tomp']

        # Save the updated DataFrame back to Excel
        df.to_excel('data of pore app/suivi de remise des EPI 1.xlsx', index=False, engine='openpyxl')

        flash("Record updated successfully!", "success")
        return redirect(url_for('view_epi1'))

    # Retrieve the record to update based on row_id
    record = df.iloc[row_id].to_dict()

    return render_template('update_epi1.html', record=record)


@app.route('/delete_epi/<int:row_id>', methods=['GET', 'POST'])
def delete_epi(row_id):
    # Charger le fichier Excel dans un DataFrame
    df = pd.read_excel('data of pore app/suivi de remise des EPI Finale.xlsx', engine='openpyxl')

    if request.method == 'POST':
        # Vérifier si l'utilisateur a confirmé la suppression
        if request.form['confirm'] == 'yes':
            # Supprimer l'enregistrement à l'index spécifié (row_id)
            df.drop(row_id, inplace=True)
            
            # Enregistrer le DataFrame mis à jour dans le fichier Excel
            df.to_excel('data of pore app/suivi de remise des EPI Finale.xlsx', index=False, engine='openpyxl')
            log_action("Suppresion Epi")
            flash("Record deleted successfully!", "success")
            return redirect(url_for('view_epi'))

    # Récupérer l'enregistrement à supprimer basé sur row_id
    record = df.iloc[row_id].to_dict()

    return render_template('delete_epi.html', record=record)


@app.route('/delete_epi1/<int:row_id>', methods=['GET', 'POST'])
def delete_epi1(row_id):
    # Load the Excel file into a DataFrame
    df = pd.read_excel('data of pore app/suivi de remise des EPI 1.xlsx', engine='openpyxl')

    if request.method == 'POST':
        # Check if the user has confirmed the deletion
        if request.form['confirm'] == 'yes':
            # Delete the record at the specified row_id
            df.drop(row_id, inplace=True)
            
            # Save the updated DataFrame back to Excel
            df.to_excel('data of pore app/suivi de remise des EPI 1.xlsx', index=False, engine='openpyxl')

            flash("Record deleted successfully!", "success")
        return redirect(url_for('view_epi1'))

    # Retrieve the record to delete based on row_id
    record = df.iloc[row_id].to_dict()

    return render_template('delete_epi1.html', record=record)

@app.route('/view_registre', methods=['GET', 'POST'])
def view_registre():
   
    excel_file = r'data of pore app/Registre du suivi des actions disciplinaires.xlsx'
    df = pd.read_excel(excel_file, engine='openpyxl')

    # Traitement des colonnes de date si nécessaire
    date_columns = []  # Ajoutez ici les colonnes de date à traiter, si besoin

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    columns = df.columns.tolist()
    data = df.to_dict(orient='records')

    if request.method == 'POST':
        search_criterion = request.form.get('search_criterion')
        search_value = request.form.get('search_value')
        if search_criterion and search_value:
            data = [row for row in data if search_value.lower() in str(row.get(search_criterion, '')).lower()]

    # Pagination
    page = int(request.args.get('page', 1))  # Numéro de page (défaut à 1)
    per_page = 20  # Nombre de lignes par page
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_data = data[start:end]
    total_pages = (total + per_page - 1) // per_page  # Calcul du nombre total de pages

    return render_template('view_registre.html',
                           data=paginated_data,
                           columns=columns,
                           page=page,
                           total_pages=total_pages,
                           max=max,
                           min=min)

@app.route('/add_registre', methods=['GET', 'POST'])
def add_registre():
    if request.method == 'POST':
        # Get the form data
        form_data = {
            'Date': request.form['date'],
            'Emetteur': request.form['emetteur'],
            'Violateur': request.form['violateur'],
            'Fonction': request.form['fonction'],
            'MAT': request.form['matricule'],
            'Zone d\'activité': request.form['zone_activite'],
            'Organisme': request.form['organisme'],
            'Description de l\'infraction': request.form['description_infraction'],
            'WPS (Worst Potential Severity)': request.form['wps'],
            'Catégorie': request.form['categorie'],
            'Observations Type (Positive=P/ Negative=N)': request.form['observations_type'],
            'Risque associé': request.form['risque_associe'],
            'Evidence Reference': request.form['evidence_reference'],
            'Actions': request.form['actions'],
            'Status (Ouvert/Fermé/En cours)': request.form['status'],
            'Remarques': request.form['remarques'],
            'Nombre d\'avertissements': request.form['nombre_avertissements']
        }

        try:
            # Charger le fichier Excel existant
            df = pd.read_excel('data of pore app/Registre du suivi des actions disciplinaires.xlsx', engine='openpyxl')

            # Vérifier si le DataFrame chargé est vide
            if df.empty:
                # Créer un nouveau DataFrame avec les colonnes définies
                df = pd.DataFrame(columns=['Date', 'Emetteur', 'Violateur', 'Fonction', 'MAT', 'Zone d\'activité', 
                                           'Organisme', 'Description de l\'infraction', 'WPS (Worst Potential Severity)', 
                                           'Catégorie', 'Observations Type (Positive=P/ Negative=N)', 'Risque associé', 
                                           'Evidence Reference', 'Actions', 'Status (Ouvert/Fermé/En cours)', 'Remarques', 
                                           'Nombre d\'avertissements'])

            # Créer un nouveau DataFrame pour le nouvel enregistrement
            new_record = pd.DataFrame([form_data])

            # Concaténer le nouveau record avec le DataFrame existant
            df = pd.concat([df, new_record], ignore_index=True)

            # Remplir les valeurs NaN dans la colonne Fonction avec ''
            df['Fonction'].fillna('', inplace=True)

            # Réorganiser les colonnes pour garantir l'ordre correct
            df = df[['Date', 'Emetteur', 'Violateur', 'Fonction', 'MAT', 'Zone d\'activité', 
                     'Organisme', 'Description de l\'infraction', 'WPS (Worst Potential Severity)', 
                     'Catégorie', 'Observations Type (Positive=P/ Negative=N)', 'Risque associé', 
                     'Evidence Reference', 'Actions', 'Status (Ouvert/Fermé/En cours)', 'Remarques', 
                     'Nombre d\'avertissements']]

            # Sauvegarder le DataFrame mis à jour dans le fichier Excel
            df.to_excel('data of pore app/Registre du suivi des actions disciplinaires.xlsx', index=False, engine='openpyxl')
            log_action("Ajout d'un nouveau sanction")
            flash("New record added successfully!", "success")
            return redirect(url_for('view_registre'))

        except FileNotFoundError:
            flash("File not found: 'data of pore app/Registre du suivi des actions disciplinaires.xlsx'", "danger")
            return redirect(url_for('add_registre'))

    return render_template('add_registre.html')


@app.route('/update_registre/<int:row_id>', methods=['GET', 'POST'])
def update_registre(row_id):
    # Lire le fichier Excel
    df = pd.read_excel('data of pore app/Registre du suivi des actions disciplinaires.xlsx', engine='openpyxl')
    
    if request.method == 'POST':
        # Obtenir les données du formulaire
        form_data = {
            'Date': request.form['date'],
            'Emetteur': request.form['emetteur'],
            'Violateur': request.form['violateur'],
            'Fonction': request.form['fonction'],
            'MAT': request.form['matricule'],
            'Zone d\'activité': request.form['zone_activite'],
            'Organisme': request.form['organisme'],
            'Description de l\'infraction': request.form['description_infraction'],
            'WPS (Worst Potential Severity)': request.form['wps'],
            'Catégorie': request.form['categorie'],
            'Observations Type (Positive=P/ Negative=N)': request.form['observations_type'],
            'Risque associé': request.form['risque_associe'],
            'Evidence Reference': request.form['evidence_reference'],
            'Actions': request.form['actions'],
            'Status (Ouvert/Fermé/En cours)': request.form['status'],
            'Remarques': request.form['remarques'],
            'Nombre d\'avertissements': request.form['nombre_avertissements']
        }

        # Mettre à jour le DataFrame
        for key, value in form_data.items():
            df.at[row_id, key] = value

        # Sauvegarder le DataFrame mis à jour dans le fichier Excel
        df.to_excel('data of pore app/Registre du suivi des actions disciplinaires.xlsx', index=False, engine='openpyxl')
        log_action("Mise à jour de sanction")
        flash("Record updated successfully!", "success")
        return redirect(url_for('view_registre'))

    # Obtenir les données de la ligne à mettre à jour
    record = df.iloc[row_id]

    return render_template('update_registre.html', record=record, row_id=row_id)
@app.route('/delete_registre/<int:row_id>', methods=['GET', 'POST'])
def delete_registre(row_id):
    # Charger le fichier Excel dans un DataFrame
    df = pd.read_excel('data of pore app/Registre du suivi des actions disciplinaires.xlsx', engine='openpyxl')

    if request.method == 'POST':
        # Vérifier si le champ 'confirm' est présent dans request.form
        confirm = request.form.get('confirm')
        if confirm == 'yes':
            # Supprimer l'enregistrement à l'index spécifié
            df.drop(row_id, inplace=True)
            
            # Réindexer le DataFrame après suppression
            df.reset_index(drop=True, inplace=True)
            
            # Sauvegarder le DataFrame mis à jour dans le fichier Excel
            df.to_excel('data of pore app/Registre du suivi des actions disciplinaires.xlsx', index=False, engine='openpyxl')
            log_action("Suppresion de sanction")
            flash("Record deleted successfully!", "success")
            return redirect(url_for('view_registre'))  # Rediriger après la suppression

    # Récupérer l'enregistrement à supprimer basé sur row_id
    record = df.iloc[row_id].to_dict()

    return render_template('delete_registre.html', record=record)

@app.route('/import_registre', methods=['GET', 'POST'])
def import_registre():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            REGISTRE_COLUMNS = [
                'Date', 'Emetteur', 'Violateur', 'Fonction', 'MAT', 'Zone d\'activité',
                'Organisme', 'Description de l\'infraction', 'WPS (Worst Potential Severity)',
                'Catégorie', 'Observations Type (Positive=P/ Negative=N)', 'Risque associé',
                'Evidence Reference', 'Actions', 'Status (Ouvert/Fermé/En cours)', 'Remarques',
                'Nombre d\'avertissements'
            ]

            # Liste des colonnes de date spécifiques à votre fichier de registre
            date_columns = ['Date']

            # Déterminer le moteur en fonction de l'extension du fichier
            if file.filename.endswith('.xlsx'):
                engine = 'openpyxl'
            elif file.filename.endswith('.xls'):
                engine = 'xlrd'
            
            # Lire le nouveau fichier Excel
            df_new = pd.read_excel(file, engine=engine)
            # Lire le fichier Excel existant
            df_existing = pd.read_excel('data of pore app/Registre du suivi des actions disciplinaires.xlsx', engine='openpyxl')

            # Vérifier si les colonnes correspondent
            if set(df_new.columns) == set(REGISTRE_COLUMNS):
                # Convertir les colonnes de date en datetime
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_datetime(df_new[col], errors='coerce', dayfirst=True)
                    if col in df_existing.columns:
                        df_existing[col] = pd.to_datetime(df_existing[col], errors='coerce', dayfirst=True)

                # Remplacer les dates NaT par des valeurs vides
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = df_new[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')
                    if col in df_existing.columns:
                        df_existing[col] = df_existing[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')

                # Combiner les DataFrames et supprimer les doublons
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates().reset_index(drop=True)
                # Enregistrer le fichier Excel combiné
                df_combined.to_excel('data of pore app/Registre du suivi des actions disciplinaires.xlsx', index=False, engine='openpyxl')
                log_action("Importation nouveaux sanctions")
                flash("Fichier importé et fusionné avec succès !", "success")
            else:
                flash("Les colonnes du fichier importé ne correspondent pas au tableau existant.", "danger")
        else:
            flash("Veuillez télécharger un fichier Excel valide (.xlsx ou .xls).", "danger")

        return redirect(url_for('view_registre'))  # Assurez-vous que cette route existe
    
    return render_template('import_registre.html')  # Créez le template pour cette vue



@app.route('/view_formation', methods=['GET', 'POST'])
def view_formation():
    excel_file = r'data of pore app\fiche formation finale.xlsx'
    df = pd.read_excel(excel_file, engine='openpyxl')

    # Traitement des colonnes de date si nécessaire
    # Exemple : Ajouter des colonnes de date à traiter
    date_columns = []  # Ajoutez ici les colonnes de date qui doivent être traitées

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    columns = df.columns.tolist()
    data = df.to_dict(orient='records')

    if request.method == 'POST':
        search_criterion = request.form.get('search_criterion')
        search_value = request.form.get('search_value')
        if search_criterion and search_value:
            data = [row for row in data if search_value.lower() in str(row.get(search_criterion, '')).lower()]

    # Pagination
    page = int(request.args.get('page', 1))  # Numéro de page (défaut à 1)
    per_page = 20  # Nombre de lignes par page
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_data = data[start:end]
    total_pages = (total + per_page - 1) // per_page  # Calcul du nombre total de pages

    return render_template('view_formation.html',
                           data=paginated_data,
                           columns=columns,
                           page=page,
                           total_pages=total_pages,
                           max=max,
                           min=min)


COLUMNS = [
    'AFFEECTATION', 'MAT', 'NOM ET PRENOM', 'FONCTION', 'CIN', 'D EMBAUCHE', 'SECTION',
    'Formation sur prévention des risques électriques: Nombre', 'Formation sur prévention des risques électriques: Date',
    'Formation sur les techniques d\'elingage en sécurité: Nombre', 'Formation sur les techniques d\'elingage en sécurité: Date',
    'Formation sur les travaux en hauteur: Nombre', 'Formation sur les travaux en hauteur: Date',
    'Formation sur les travaux offshores: Nombre', 'Formation sur les travaux offshores: Date',
    'Formation sur des signaleurs: Nombre', 'Formation sur des signaleurs: Date',
    'Formation sur la conduite en sécurité sur chantier: Nombre', 'Formation sur la conduite en sécurité sur chantier: Date',
    'Formation sur les équipements mobiles et circulation: Nombre', 'Formation sur les équipements mobiles et circulation: Date',
    'Formation sur l\'usage sécuritaire de l\'échafaudage: Nombre', 'Formation sur l\'usage sécuritaire de l\'échafaudage: Date',
    'Formation sur le respect du 5S: Nombre', 'Formation sur le respect du 5S: Date',
    'Formation sur la necessité du vigilence et port des EPI: Nombre', 'Formation sur la necessité du vigilence et port des EPI: Date',
    'Formation sur la prévention des risques des travaux maritimes: Nombre', 'Formation sur la prévention des risques des travaux maritimes: Date',
    'Formation sur les travaux à proximité de l\'eau / la mer: Nombre', 'Formation sur les travaux à proximité de l\'eau / la mer: Date',
    'Formation sur la prévention les risques des travaux ferraillage: Nombre', 'Formation sur la prévention les risques des travaux ferraillage: Date',
    'Formation sur l\'intervention sécuritaire en espace confiné: Nombre', 'Formation sur l\'intervention sécuritaire en espace confiné: Date',
    'Formation sur la consignation-déconsignation: Nombre', 'Formation sur la consignation-déconsignation: Date',
    'Formation sur les risques liés aux opération de levage: Nombre', 'Formation sur les risques liés aux opération de levage: Date',
    'Formation sur le sauvetage-secourisme au travail: Nombre', 'Formation sur le sauvetage-secourisme au travail: Date',
    'Formation sur la prévention des risques liées au chargement et déchargement des tubes métallique: Nombre', 'Formation sur la prévention des risques liées au chargement et déchargement des tubes métallique: Date',
    'Formation sur l\'usage sécuritaire des appareils électroportatifs.(HILTI): Nombre', 'Formation sur l\'usage sécuritaire des appareils électroportatifs.(HILTI): Date',
    'Formation sur les risques du démontage de la structure méttalique: Nombre', 'Formation sur les risques du démontage de la structure méttalique: Date',
    'Formation incendie: Nombre', 'Formation incendie: Date',
    'Formation sur les gestes du guidages: Nombre', 'Formation sur les gestes du guidages: Date',
    'Formation sur prévention de noyad: Nombre', 'Formation sur prévention de noyad: Date',
    'Formation sur la gestion du stress au travail: Nombre', 'Formation sur la gestion du stress au travail: Date',
    'Formation sur les risques liés au démontage de la charpente métallique: Nombre', 'Formation sur les risques liés au démontage de la charpente métallique: Date',
    'Formation sur l\'inspection des amoires électrique: Nombre', 'Formation sur l\'inspection des amoires électrique: Date',
    'Formation sur procédure de plongée: Nombre', 'Formation sur procédure de plongée: Date',
    'Techniques d\'élingage-désélingage / mantaention manuelle PRATIQUE: Nombre', 'Techniques d\'élingage-désélingage / mantaention manuelle PRATIQUE: Date',
    'Formation sur les gestes et postures: Nombre', 'Formation sur les gestes et postures: Date',
    'Formation sur les gestes et postures PRATIQUE: Nombre', 'Formation sur les gestes et postures PRATIQUE: Date',
    'formation sur eagle eyes: Nombre', 'formation sur eagle eyes: Date',
    'Formation sur la gestion des déchets: Nombre', 'Formation sur la gestion des déchets: Date',
    'Formation sur la conduite à tenir en cas de déversement accidentel: Nombre', 'Formation sur la conduite à tenir en cas de déversement accidentel: Date',
    'Formation sur la conduite à tenir en cas de déversement accidentel /PRATIQUE/: Nombre', 'Formation sur la conduite à tenir en cas de déversement accidentel /PRATIQUE/: Date',
    'Formation sur incidents environnementaux: Nombre', 'Formation sur incidents environnementaux: Date',
    'Formation sur les risques environnementaux: Nombre', 'Formation sur les risques environnementaux: Date',
    'Formation les risqus des poussiéres: Nombre', 'Formation les risqus des poussiéres: Date',
    'Formation sur produits chimiques et pictogrammes de dangers: Nombre', 'Formation sur produits chimiques et pictogrammes de dangers: Date',
    'Formation sur la procédure de gestion des matiéres dangereuses: Nombre', 'Formation sur la procédure de gestion des matiéres dangereuses: Date',
    'Formation sur gestes et postures au travail - manutention manvelle: Nombre', 'Formation sur gestes et postures au travail - manutention manvelle: Date',
    'Formation sur l\'usage de bouée sauvetage: Nombre', 'Formation sur l\'usage de bouée sauvetage: Date',
    'Formation sur les équipements mobiles et circulation-la conduite en sécurite sur chantier(CHAUFFEUR): Nombre', 'Formation sur les équipements mobiles et circulation-la conduite en sécurite sur chantier(CHAUFFEUR): Date',
    'Formation sur les risques liés aux travaux de sablage: Nombre', 'Formation sur les risques liés aux travaux de sablage: Date',
    'Formation de sécourisme au travail: Nombre', 'Formation de sécourisme au travail: Date',
    'Formation sur les mettodes et techniques utilisation des accesoires de sauvetage: Nombre', 'Formation sur les mettodes et techniques utilisation des accesoires de sauvetage: Date',
    'Formation sur l\'usage sécuritaire des appareils électroportatifs: Nombre', 'Formation sur l\'usage sécuritaire des appareils électroportatifs: Date',
    'Formation sur l\'usage sécuritaire de l\'échafaudage: Nombre', 'Formation sur l\'usage sécuritaire de l\'échafaudage: Date',
    'Formation sur l\'inspection des amoires électrique: Nombre.1', 'Formation sur l\'inspection des amoires électrique: Date.1',
    'Formation sur l\'inspection des amoires électrique: Nombre.2', 'Formation sur l\'inspection des amoires électrique: Date.2',
    'Formation sur mesures de sécurité: équipage mobile- démarrage TCO: Nombre', 'Formation sur mesures de sécurité: équipage mobile- démarrage TCO: Date',
    'Formation sur les risques et méthodes de prevention liees au travaux d\'amarrage et traction par treuil: Nombre', 'Formation sur les risques et méthodes de prevention liees au travaux d\'amarrage et traction par treuil: Date',
    'Formation sur inspection et usage du gilet de sauvetage : Nombre', 'Formation sur inspection et usage du gilet de sauvetage : Date',
    'Formation sur les techniques d\'embarquement et debarquement: Nombre', 'Formation sur les techniques d\'embarquement et debarquement: Date',
    'Formation sur la prevention des risques liés à l\'exposition au bruit: Nombre', 'Formation sur la prevention des risques liés à l\'exposition au bruit: Date',
    'Formation sur les risques existant à la CAB : nombre', 'Formation sur les risques existant à la CAB : Date',
    'Formation sur le sauvetage-secourisme au travail.(C R ): Nombre', 'Formation sur le sauvetage-secourisme au travail.(C R ): Date',
    'Formation sur equipements de sauvetage maritimes: Nombre', 'Formation sur equipements de sauvetage maritimes: Date'
]


@app.route('/add_formation', methods=['GET', 'POST'])
def add_formation():
    if request.method == 'POST':
        data = {col: request.form.get(col, '') for col in COLUMNS}
        df = pd.DataFrame([data])
        excel_file = r'data of pore app\fiche formation finale.xlsx'
        
        # Lecture du fichier Excel existant s'il existe
        if os.path.exists(excel_file):
            existing_df = pd.read_excel(excel_file)
            updated_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            # Si le fichier n'existe pas, on crée un nouveau DataFrame avec les données entrées
            updated_df = df
        
        # Écriture des données mises à jour dans le fichier Excel
        updated_df.to_excel(excel_file, index=False, engine='openpyxl')
        log_action("Ajout d'une formation")
        flash("Nouvel enregistrement ajouté avec succès !", "success")
        return redirect(url_for('view_formation'))
    
    return render_template('add_formation.html', columns=COLUMNS)


@app.route('/update_formation/<int:index>', methods=['GET', 'POST'])
def update_formation(index):
    excel_file = r'data of pore app\fiche formation finale.xlsx'
    df = pd.read_excel(excel_file)

    if request.method == 'POST':
        for col in COLUMNS:
            df.at[index, col] = request.form.get(col, '')
        df.to_excel(excel_file, index=False, engine='openpyxl')
        log_action("Mise à jour de formation")
        flash("Enregistrement mis à jour avec succès !", "success")
        return redirect(url_for('view_formation'))

    data = df.iloc[index].to_dict()
    return render_template('update_formation.html', index=index, data=data, columns=COLUMNS)


@app.route('/confirm_delete_formation/<int:index>', methods=['GET', 'POST'])
def confirm_delete_formation(index):
    excel_file = r'data of pore app\fiche formation finale.xlsx'
    df = pd.read_excel(excel_file)
    data = df.iloc[index].to_dict()

    if request.method == 'POST':
        # Suppression de l'enregistrement
        df = df.drop(index)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        flash("Enregistrement supprimé avec succès !", "success")
        log_action("Suppresion d'une formation")
        return redirect(url_for('view_formation'))

    return render_template('delete_formation.html', index=index, data=data, columns=COLUMNS)

@app.route('/import_formation', methods=['GET', 'POST'])
def import_formation():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            # Définir les colonnes
            COLUMNS = [
                'AFFEECTATION', 'MAT', 'NOM ET PRENOM', 'FONCTION', 'CIN', 'D EMBAUCHE', 'SECTION',
                'Formation sur prévention des risques électriques: Nombre', 'Formation sur prévention des risques électriques: Date',
                'Formation sur les techniques d\'elingage en sécurité: Nombre', 'Formation sur les techniques d\'elingage en sécurité: Date',
                'Formation sur les travaux en hauteur: Nombre', 'Formation sur les travaux en hauteur: Date',
                'Formation sur les travaux offshores: Nombre', 'Formation sur les travaux offshores: Date',
                'Formation sur des signaleurs: Nombre', 'Formation sur des signaleurs: Date',
                'Formation sur la conduite en sécurité sur chantier: Nombre', 'Formation sur la conduite en sécurité sur chantier: Date',
                'Formation sur les équipements mobiles et circulation: Nombre', 'Formation sur les équipements mobiles et circulation: Date',
                'Formation sur l\'usage sécuritaire de l\'échafaudage: Nombre', 'Formation sur l\'usage sécuritaire de l\'échafaudage: Date',
                'Formation sur le respect du 5S: Nombre', 'Formation sur le respect du 5S: Date',
                'Formation sur la necessité du vigilence et port des EPI: Nombre', 'Formation sur la necessité du vigilence et port des EPI: Date',
                'Formation sur la prévention des risques des travaux maritimes: Nombre', 'Formation sur la prévention des risques des travaux maritimes: Date',
                'Formation sur les travaux à proximité de l\'eau / la mer: Nombre', 'Formation sur les travaux à proximité de l\'eau / la mer: Date',
                'Formation sur la prévention les risques des travaux ferraillage: Nombre', 'Formation sur la prévention les risques des travaux ferraillage: Date',
                'Formation sur l\'intervention sécuritaire en espace confiné: Nombre', 'Formation sur l\'intervention sécuritaire en espace confiné: Date',
                'Formation sur la consignation-déconsignation: Nombre', 'Formation sur la consignation-déconsignation: Date',
                'Formation sur les risques liés aux opération de levage: Nombre', 'Formation sur les risques liés aux opération de levage: Date',
                'Formation sur le sauvetage-secourisme au travail: Nombre', 'Formation sur le sauvetage-secourisme au travail: Date',
                'Formation sur la prévention des risques liées au chargement et déchargement des tubes métallique: Nombre', 'Formation sur la prévention des risques liées au chargement et déchargement des tubes métallique: Date',
                'Formation sur l\'usage sécuritaire des appareils électroportatifs.(HILTI): Nombre', 'Formation sur l\'usage sécuritaire des appareils électroportatifs.(HILTI): Date',
                'Formation sur les risques du démontage de la structure méttalique: Nombre', 'Formation sur les risques du démontage de la structure méttalique: Date',
                'Formation incendie: Nombre', 'Formation incendie: Date',
                'Formation sur les gestes du guidages: Nombre', 'Formation sur les gestes du guidages: Date',
                'Formation sur prévention de noyad: Nombre', 'Formation sur prévention de noyad: Date',
                'Formation sur la gestion du stress au travail: Nombre', 'Formation sur la gestion du stress au travail: Date',
                'Formation sur les risques liés au démontage de la charpente métallique: Nombre', 'Formation sur les risques liés au démontage de la charpente métallique: Date',
                'Formation sur l\'inspection des amoires électrique: Nombre', 'Formation sur l\'inspection des amoires électrique: Date',
                'Formation sur procédure de plongée: Nombre', 'Formation sur procédure de plongée: Date',
                'Techniques d\'élingage-désélingage / mantaention manuelle PRATIQUE: Nombre', 'Techniques d\'élingage-désélingage / mantaention manuelle PRATIQUE: Date',
                'Formation sur les gestes et postures: Nombre', 'Formation sur les gestes et postures: Date',
                'Formation sur les gestes et postures PRATIQUE: Nombre', 'Formation sur les gestes et postures PRATIQUE: Date',
                'formation sur eagle eyes: Nombre', 'formation sur eagle eyes: Date',
                'Formation sur la gestion des déchets: Nombre', 'Formation sur la gestion des déchets: Date',
                'Formation sur la conduite à tenir en cas de déversement accidentel: Nombre', 'Formation sur la conduite à tenir en cas de déversement accidentel: Date',
                'Formation sur la conduite à tenir en cas de déversement accidentel /PRATIQUE/: Nombre', 'Formation sur la conduite à tenir en cas de déversement accidentel /PRATIQUE/: Date',
                'Formation sur incidents environnementaux: Nombre', 'Formation sur incidents environnementaux: Date',
                'Formation sur les risques environnementaux: Nombre', 'Formation sur les risques environnementaux: Date',
                'Formation les risqus des poussiéres: Nombre', 'Formation les risqus des poussiéres: Date',
                'Formation sur produits chimiques et pictogrammes de dangers: Nombre', 'Formation sur produits chimiques et pictogrammes de dangers: Date',
                'Formation sur la procédure de gestion des matiéres dangereuses: Nombre', 'Formation sur la procédure de gestion des matiéres dangereuses: Date',
                'Formation sur gestes et postures au travail - manutention manvelle: Nombre', 'Formation sur gestes et postures au travail - manutention manvelle: Date',
                'Formation sur l\'usage de bouée sauvetage: Nombre', 'Formation sur l\'usage de bouée sauvetage: Date',
                'Formation sur les équipements mobiles et circulation-la conduite en sécurite sur chantier(CHAUFFEUR): Nombre', 'Formation sur les équipements mobiles et circulation-la conduite en sécurite sur chantier(CHAUFFEUR): Date',
                'Formation sur les risques liés aux travaux de sablage: Nombre', 'Formation sur les risques liés aux travaux de sablage: Date',
                'Formation de sécourisme au travail: Nombre', 'Formation de sécourisme au travail: Date',
                'Formation sur les mettodes et techniques utilisation des accesoires de sauvetage: Nombre', 'Formation sur les mettodes et techniques utilisation des accesoires de sauvetage: Date',
                'Formation sur l\'usage sécuritaire des appareils électroportatifs: Nombre', 'Formation sur l\'usage sécuritaire des appareils électroportatifs: Date',
                'Formation sur l\'usage sécuritaire de l\'échafaudage: Nombre', 'Formation sur l\'usage sécuritaire de l\'échafaudage: Date',
                'Formation sur l\'inspection des amoires électrique: Nombre.1', 'Formation sur l\'inspection des amoires électrique: Date.1',
                'Formation sur l\'inspection des amoires électrique: Nombre.2', 'Formation sur l\'inspection des amoires électrique: Date.2',
                'Formation sur mesures de sécurité: équipage mobile- démarrage TCO: Nombre', 'Formation sur mesures de sécurité: équipage mobile- démarrage TCO: Date',
                'Formation sur les risques et méthodes de prevention liees au travaux d\'amarrage et traction par treuil: Nombre', 'Formation sur les risques et méthodes de prevention liees au travaux d\'amarrage et traction par treuil: Date',
                'Formation sur inspection et usage du gilet de sauvetage : Nombre', 'Formation sur inspection et usage du gilet de sauvetage : Date',
                'Formation sur les techniques d\'embarquement et debarquement: Nombre', 'Formation sur les techniques d\'embarquement et debarquement: Date',
                'Formation sur la prevention des risques liés à l\'exposition au bruit: Nombre', 'Formation sur la prevention des risques liés à l\'exposition au bruit: Date',
                'Formation sur les risques existant à la CAB : nombre', 'Formation sur les risques existant à la CAB : Date',
                'Formation sur le sauvetage-secourisme au travail.(C R ): Nombre', 'Formation sur le sauvetage-secourisme au travail.(C R ): Date',
                'Formation sur equipements de sauvetage maritimes: Nombre', 'Formation sur equipements de sauvetage maritimes: Date'
]

            # Liste des colonnes de date spécifiques à votre fichier de formation
            date_columns = [col for col in COLUMNS if 'Date' in col]

            # Déterminer le moteur en fonction de l'extension du fichier
            engine = 'openpyxl' if file.filename.endswith('.xlsx') else 'xlrd'

            # Lire le nouveau fichier Excel
            df_new = pd.read_excel(file, engine=engine)
            # Lire le fichier Excel existant
            df_existing = pd.read_excel('data of pore app/fiche formation finale.xlsx', engine='openpyxl')

            # Vérifier si les colonnes correspondent
            if set(df_new.columns) == set(df_existing.columns):
                # Convertir les colonnes de date en datetime
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_datetime(df_new[col], errors='coerce', dayfirst=True)
                    if col in df_existing.columns:
                        df_existing[col] = pd.to_datetime(df_existing[col], errors='coerce', dayfirst=True)

                # Remplacer les dates NaT par des valeurs vides (ou une valeur par défaut si nécessaire)
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = df_new[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')
                    if col in df_existing.columns:
                        df_existing[col] = df_existing[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')

                # Combiner les DataFrames et supprimer les doublons
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates().reset_index(drop=True)
                # Enregistrer le fichier Excel combiné
                df_combined.to_excel('data of pore app/fiche formation finale.xlsx', index=False, engine='openpyxl')
                log_action("Importation d'une formation")
                flash("Fichier importé et fusionné avec succès !", "success")
            else:
                flash("Les colonnes du fichier importé ne correspondent pas au tableau existant.", "danger")
        else:
            flash("Veuillez télécharger un fichier Excel valide (.xlsx ou .xls).", "danger")

        return redirect(url_for('view_formation'))
    
    return render_template('import_formation.html')



SENS_COLUMNS = [
    'AFFEECTATION', 'MAT', 'NOM ET PRENOM', 'FONCTION', 'CIN', 'D EMBAUCHE', 'SECTION',
    'Sensibilisation sur des travaux en hateur: Nombre', 'Sensibilisation sur des travaux en hateur: Date',
    'Sensibilisation sur les techniques d\'ingage: Nombre', 'Sensibilisation sur les techniques d\'ingage: Date',
    'Sensibilisation sur les risques des maladiers professionnelle et les prévention à prendre au cours de travail : Nombre',
    'Sensibilisation sur les risques des maladiers professionnelle et les prévention à prendre au cours de travail : Date',
    'Sensibilisation sur les précontions à pendant les travaux de soudage: Nombre',
    'Sensibilisation sur les précontions à pendant les travaux de soudage: Date',
    'Sensibilisation sur les risques de chut et de glissade l\'ies aux déplacements : Nombre',
    'Sensibilisation sur les risques de chut et de glissade l\'ies aux déplacements : Date',
    'Sensibilisation sur les risques électriques: Nombre', 'Sensibilisation sur les risques électriques: Date',
    'sensibilisation sur l\'importance de mettre l\'etiquatage des produits chimiques: Nombre',
    'sensibilisation sur l\'importance de mettre l\'etiquatage des produits chimiques: Date',
    'sensibilisation sur les gestes et postures au travail: Nombre', 'sensibilisation sur les gestes et postures au travail: Date',
    'senisibilisation sur les risques lieé a l\'activité physique de travail (maneutation manuelle): Nombre',
    'senisibilisation sur les risques lieé a l\'activité physique de travail (maneutation manuelle): Date',
    'Sensibilisation sur les risque covid: Nombre', 'Sensibilisation sur les risque covid: Date',
    'Sensibilisation sur les risques lieé au travaux de décharge et charge des barres de ferraillage: Nombre',
    'Sensibilisation sur les risques lieé au travaux de décharge et charge des barres de ferraillage: Date',
    'Sensibilisation incedie: Nombre', 'Sensibilisation incedie: Date',
    'Sensibilisation sur les risques lieés au travail à proximité d\'un pelle pour eviter les écrassements: Nombre',
    'Sensibilisation sur les risques lieés au travail à proximité d\'un pelle pour eviter les écrassements: Date',
    'Sensibilisation sur équipements mobiles et circulation: nombre', 'Sensibilisation sur équipements mobiles et circulation : Date',
    'Sensibilisation sur les travaux à proximité de l\'eaux / la mer: Nombre', 'Sensibilisation sur les travaux à proximité de l\'eaux / la mer: Date',
    'Sensibilisation sur les risques environnemtaux (nettoyage): Nombre', 'Sensibilisation sur les risques environnemtaux (nettoyage): Date',
    'Sensibilisation sur les travaux de sablage pour éviter les accidents: Nombre', 'Sensibilisation sur les travaux de sablage pour éviter les accidents: Date',
    'Sensibilisation sur risques lieés aux operation de levage: Nombre', 'Sensibilisation sur risques lieés aux operation de levage: Date',
    'Sensibilisation sur l\'obligation de coordination avec le serviece HSE avent de procéder aux operations critiques: Nombre',
    'Sensibilisation sur l\'obligation de coordination avec le serviece HSE avent de procéder aux operations critiques: Date',
    'Sensibilisation sur les risques de chate et de glissade l\'iees aux déplacement: Nombre',
    'Sensibilisation sur les risques de chate et de glissade l\'iees aux déplacement : Date'
]

@app.route('/view_sens', methods=['GET', 'POST'])
def view_sens():
    excel_file = r'data of pore app\Gestion des sensibilisation (1).xlsx'
    df = pd.read_excel(excel_file, engine='openpyxl')

    # Traitement des colonnes de date si nécessaire
    # Exemple : Ajouter des colonnes de date à traiter
    date_columns = []  # Ajoutez ici les colonnes de date qui doivent être traitées

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    columns = df.columns.tolist()
    data = df.to_dict(orient='records')

    if request.method == 'POST':
        search_criterion = request.form.get('search_criterion')
        search_value = request.form.get('search_value')
        if search_criterion and search_value:
            data = [row for row in data if search_value.lower() in str(row.get(search_criterion, '')).lower()]

    # Pagination
    page = int(request.args.get('page', 1))  # Numéro de page (défaut à 1)
    per_page = 20  # Nombre de lignes par page
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_data = data[start:end]
    total_pages = (total + per_page - 1) // per_page  # Calcul du nombre total de pages

    return render_template('view_sens.html',
                           data=paginated_data,
                           columns=columns,
                           page=page,
                           total_pages=total_pages,
                           max=max,
                           min=min)


@app.route('/add_sens', methods=['GET', 'POST'])
def add_sens():
    if request.method == 'POST':
        new_entry = {col: request.form.get(col, '') for col in SENS_COLUMNS}
        df = pd.read_excel(r'data of pore app\Gestion des sensibilisation (1).xlsx')
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel(r'data of pore app\Gestion des sensibilisation (1).xlsx', index=False, engine='openpyxl')
        log_action("Ajout d'une nouvelle sensibilisation")
        flash("Enregistrement ajouté avec succès !", "success")
        return redirect(url_for('view_sens'))
    return render_template('add_sens.html', columns=SENS_COLUMNS)


@app.route('/update_sens/<int:index>', methods=['GET', 'POST'])
def update_sens(index):
    excel_file = r'data of pore app\Gestion des sensibilisation (1).xlsx'  # Changez l'extension à .xlsx
    df = pd.read_excel(excel_file, engine='openpyxl')  # Utilisez openpyxl pour lire le fichier

    if request.method == 'POST':
        for col in SENS_COLUMNS:
            df.at[index, col] = request.form.get(col, '')
        df.to_excel(excel_file, index=False, engine='openpyxl')
          # Utilisez openpyxl pour écrire dans le fichier
        log_action("Mise à jour d'une sensibilisation")
        flash("Enregistrement mis à jour avec succès !", "success")
        return redirect(url_for('view_sens'))

    data = df.iloc[index].to_dict()
    return render_template('update_sens.html', index=index, data=data, columns=SENS_COLUMNS)

@app.route('/confirm_delete_sens/<int:index>', methods=['GET', 'POST'])
def confirm_delete_sens(index):
    if request.method == 'POST':
        excel_file = r'data of pore app\Gestion des sensibilisation (1).xlsx'
        df = pd.read_excel(excel_file)
        df = df.drop(index)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        log_action("Suppresion d'une sensibilisation")
        flash("Enregistrement supprimé avec succès !", "success")
        return redirect(url_for('view_sens'))

    excel_file = r'data of pore app\Gestion des sensibilisation (1).xlsx'
    df = pd.read_excel(excel_file)
    data = df.iloc[index].to_dict()
    return render_template('confirm_delete_sens.html', data=data, columns=SENS_COLUMNS, index=index)

@app.route('/import_sens', methods=['GET', 'POST'])
def import_sens():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            # Déterminer le moteur en fonction de l'extension du fichier
            engine = 'openpyxl' if file.filename.endswith('.xlsx') else 'xlrd'
            
            # Lire le nouveau fichier Excel
            df_new = pd.read_excel(file, engine=engine)
            # Lire le fichier Excel existant
            df_existing = pd.read_excel('data of pore app/Gestion des sensibilisation (1).xlsx', engine='openpyxl')

            # Vérifier si les colonnes correspondent
            if set(df_new.columns) == set(df_existing.columns):
                # Liste des colonnes contenant des dates
                date_columns = [
                    'Sensibilisation sur des travaux en hateur: Date',
                    'Sensibilisation sur les techniques d\'ingage: Date',
                    'Sensibilisation sur les risques des maladiers professionnelle et les prévention à prendre au cours de travail : Date',
                    'Sensibilisation sur les précontions à pendant les travaux de soudage: Date',
                    'Sensibilisation sur les risques de chut et de glissade l\'ies aux déplacements : Date',
                    'Sensibilisation sur les risques électriques: Date',
                    'sensibilisation sur l\'importance de mettre l\'etiquatage des produits chimiques: Date',
                    'sensibilisation sur les gestes et postures au travail: Date',
                    'senisibilisation sur les risques lieé a l\'activité physique de travail (maneutation manuelle): Date',
                    'Sensibilisation sur les risque covid: Date',
                    'Sensibilisation sur les risques lieé au travaux de décharge et charge des barres de ferraillage: Date',
                    'Sensibilisation incedie: Date',
                    'Sensibilisation sur les risques lieés au travail à proximité d\'un pelle pour eviter les écrassements: Date',
                    'Sensibilisation sur équipements mobiles et circulation : Date',
                    'Sensibilisation sur les travaux à proximité de l\'eaux / la mer: Date',
                    'Sensibilisation sur les risques environnemtaux (nettoyage): Date',
                    'Sensibilisation sur les travaux de sablage pour éviter les accidents: Date',
                    'Sensibilisation sur risques lieés aux operation de levage: Date',
                    'Sensibilisation sur l\'obligation de coordination avec le serviece HSE avent de procéder aux operations critiques: Date',
                    'Sensibilisation sur les risques de chate et de glissade l\'iees aux déplacement : Date'
                ]

                # Convertir les colonnes de date en datetime et ajouter l'heure
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_datetime(df_new[col], errors='coerce')
                    if col in df_existing.columns:
                        df_existing[col] = pd.to_datetime(df_existing[col], errors='coerce')

                # Remplacer les dates NaT par des valeurs vides (ou une valeur par défaut si nécessaire)
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = df_new[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')
                    if col in df_existing.columns:
                        df_existing[col] = df_existing[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')

                # Combiner les DataFrames et supprimer les doublons
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates().reset_index(drop=True)
                # Enregistrer le fichier Excel combiné
                df_combined.to_excel('data of pore app/Gestion des sensibilisation (1).xlsx', index=False, engine='openpyxl')
                log_action("Importation de fichier sensibilisation")
                flash("Fichier importé et fusionné avec succès !", "success")
            else:
                flash("Les colonnes du fichier importé ne correspondent pas au tableau existant.", "danger")
        else:
            flash("Veuillez télécharger un fichier Excel valide (.xlsx ou .xls).", "danger")

        return redirect(url_for('view_sens'))
    
    return render_template('import_sens.html')



# Liste des colonnes pour les accidents de travail
ACC_COLUMNS = [
    'N°', 'MAT', 'CIN', 'Nom', 'Prénom', 'Fonction', 'Affectation', 'date de l\'accident',
    'Nature de lésion', 'Nombre de jours d\'arret',
    'Nombre de jours de prolongation 1', 'Date d\'achèvement du certificat de prolongation',
    'Nombre de jours de prolongation 2', 'Date d\'achèvement du certificat de prolongation.1',
    'Nombre de jours prolongation 3', 'Date d\'achèvement du certificat de prolongation.2',
    'Nombre de jours prolongation 4', 'Date d\'achèvement du certificat de prolongation.3',
    'Nombre de jours prolongation 5', 'Date d\'achèvement du certificat de prolongation.4',
    'Nombre de jours prolongation 6', 'Date d\'achèvement du certificat de prolongation.5',
    'Nombre de jours prolongation 7', 'Date d\'achèvement du certificat de prolongation.6',
    'Nombre de jours prolongation 8', 'Date d\'achèvement du certificat de prolongation.7',
    'Nombre de jours prolongation 9', 'Date d\'achèvement du certificat de prolongation.8',
    'Nombre de jours prolongation 10', 'Date d\'achèvement du certificat de prolongation.9',
    'Nombre de jours prolongation 11', 'Date d\'achèvement du certificat de prolongation.10',
    'Date de reprise de travail', 'Certificat de guérison', '% d\'incapacité', 'Observations'
]


@app.route('/view_acc', methods=['GET', 'POST'])
def view_acc():
    excel_file = 'data of pore app/Accident de travail.xlsx'
    df = pd.read_excel(excel_file, engine='openpyxl')

    # Convertir la colonne 'MAT' en string
    if 'MAT' in df.columns:
        df['MAT'] = df['MAT'].astype(str)  # Conversion en string

    # Liste des colonnes de date
    date_columns = [
        "date de l'accident", "Date d'achèvement du certificat de prolongation",
        "Date d'achèvement du certificat de prolongation.1",
        "Date d'achèvement du certificat de prolongation.2",
        "Date d'achèvement du certificat de prolongation.3",
        "Date d'achèvement du certificat de prolongation.4",
        "Date d'achèvement du certificat de prolongation.5",
        "Date d'achèvement du certificat de prolongation.6",
        "Date d'achèvement du certificat de prolongation.7",
        "Date d'achèvement du certificat de prolongation.8",
        "Date d'achèvement du certificat de prolongation.9",
        "Date d'achèvement du certificat de prolongation.10",
        "Date de reprise de travail"
    ]

    # Convertir les colonnes de date au format string 'YYYY-MM-DD'
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    # Traitement de la recherche
    search_criterion = request.form.get('search_criterion')
    search_value = request.form.get('search_value')
    if search_criterion and search_value:
        df = df[df[search_criterion].astype(str).str.contains(search_value, case=False, na=False)]

    columns = df.columns.tolist()
    data = df.to_dict(orient='records')

    # Pagination
    total_records = len(data)
    page = request.args.get('page', 1, type=int)
    page_size = 10  # Définissez votre taille de page ici
    total_pages = (total_records + page_size - 1) // page_size  # Calcul du nombre total de pages

    start_index = (page - 1) * page_size
    end_index = min(page * page_size, total_records)

    # Calculate pagination limits for the template
    pagination_start = max(1, page - 5)
    pagination_end = min(total_pages, page + 4)

    return render_template('view_acc.html', data=data[start_index:end_index], columns=columns,
                           total_records=total_records, page=page, page_size=page_size,
                           total_pages=total_pages, start_index=start_index, end_index=end_index,
                           pagination_start=pagination_start, pagination_end=pagination_end)



@app.route('/add_acc', methods=['GET', 'POST'])
def add_acc():
    if request.method == 'POST':
        new_entry = {col: request.form.get(col, '') for col in ACC_COLUMNS}
        df = pd.read_excel('data of pore app/Accident de travail.xlsx', engine='openpyxl')
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel('data of pore app/Accident de travail.xlsx', index=False, engine='openpyxl')
        log_action("Ajout d'un accident de travail")
        flash("Enregistrement ajouté avec succès !", "success")
        return redirect(url_for('view_acc'))
    return render_template('add_acc.html', columns=ACC_COLUMNS)

@app.route('/update_acc/<int:index>', methods=['GET', 'POST'])
def update_acc(index):
    excel_file = 'data of pore app/Accident de travail.xlsx'
    df = pd.read_excel(excel_file, engine='openpyxl')

    if request.method == 'POST':
        for col in ACC_COLUMNS:
            df.at[index, col] = request.form.get(col, '')
        df.to_excel(excel_file, index=False, engine='openpyxl')
        log_action("Mise à jour de Accident de travail")
        flash("Enregistrement mis à jour avec succès !", "success")
        return redirect(url_for('view_acc'))

    data = df.iloc[index].to_dict()
    return render_template('update_acc.html', index=index, data=data, columns=ACC_COLUMNS)

@app.route('/confirm_delete_acc/<int:index>', methods=['GET', 'POST'])
def confirm_delete_acc(index):
    if request.method == 'POST':
        excel_file = 'data of pore app/Accident de travail.xlsx'
        df = pd.read_excel(excel_file, engine='openpyxl')
        df = df.drop(index)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        log_action("Suppression de accident de travail")
        flash("Enregistrement supprimé avec succès !", "success")
        return redirect(url_for('view_acc'))

    excel_file = 'data of pore app/Accident de travail.xlsx'
    df = pd.read_excel(excel_file, engine='openpyxl')
    data = df.iloc[index].to_dict()
    return render_template('confirm_delete_acc.html', data=data, columns=ACC_COLUMNS, index=index)

@app.route('/import_acc', methods=['GET', 'POST'])
def import_acc():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            # Liste des colonnes de date
            date_columns = [
                "date de l'accident", "Date d'achèvement du certificat de prolongation",
                "Date d'achèvement du certificat de prolongation.1",
                "Date d'achèvement du certificat de prolongation.2",
                "Date d'achèvement du certificat de prolongation.3",
                "Date d'achèvement du certificat de prolongation.4",
                "Date d'achèvement du certificat de prolongation.5",
                "Date d'achèvement du certificat de prolongation.6",
                "Date d'achèvement du certificat de prolongation.7",
                "Date d'achèvement du certificat de prolongation.8",
                "Date d'achèvement du certificat de prolongation.9",
                "Date d'achèvement du certificat de prolongation.10",
                "Date de reprise de travail"
            ]

            # Déterminer le moteur en fonction de l'extension du fichier
            if file.filename.endswith('.xlsx'):
                engine = 'openpyxl'
            elif file.filename.endswith('.xls'):
                engine = 'xlrd'
            
            # Lire le nouveau fichier Excel
            df_new = pd.read_excel(file, engine=engine)
            # Lire le fichier Excel existant
            df_existing = pd.read_excel('data of pore app/Accident de travail.xlsx', engine='openpyxl')

            # Vérifier si les colonnes correspondent
            if set(df_new.columns) == set(df_existing.columns):
                # Convertir les colonnes de date en datetime et ajouter l'heure
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_datetime(df_new[col], errors='coerce', dayfirst=True)
                    if col in df_existing.columns:
                        df_existing[col] = pd.to_datetime(df_existing[col], errors='coerce', dayfirst=True)

                # Remplacer les dates NaT par des valeurs vides (ou une valeur par défaut si nécessaire)
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = df_new[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')
                    if col in df_existing.columns:
                        df_existing[col] = df_existing[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')

                # Combiner les DataFrames et supprimer les doublons
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates().reset_index(drop=True)
                # Enregistrer le fichier Excel combiné
                df_combined.to_excel('data of pore app/Accident de travail.xlsx', index=False, engine='openpyxl')
                log_action("Importation de nouveaux accident de travail")
                flash("Fichier importé et fusionné avec succès !", "success")
            else:
                flash("Les colonnes du fichier importé ne correspondent pas au tableau existant.", "danger")
        else:
            flash("Veuillez télécharger un fichier Excel valide (.xlsx ou .xls).", "danger")

        return redirect(url_for('view_acc'))
    
    return render_template('import_acc.html')



DISCIPLINE_COLUMNS = [
    'MAT', 'CIN', 'Emetteur', 'Violateur', 'Fonction', 'Date', 'Organisme', 'Motif de sanction 1', 'Type de sanction 1', 'Motif de sanction 2', 'Type de sanction 2', 'Motif de sanction 3', 'Type de sanction 3', 'Observations'
]

@app.route('/view_discipline', methods=['GET', 'POST'])
def view_discipline():
    excel_file = 'data of pore app/Suivi des mesures disciplinaires.xlsx'
    df = pd.read_excel(excel_file, engine='openpyxl')

      # Convertir en entier, avec gestion des erreurs

    # Convertir la colonne de date au format string 'YYYY-MM-DD'
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Date'] = df['Date'].apply(lambda x: '' if pd.isna(x) else x.strftime('%Y-%m-%d'))

    columns = df.columns.tolist()
    data = df.to_dict(orient='records')

    if request.method == 'POST':
        search_criterion = request.form.get('search_criterion')
        search_value = request.form.get('search_value')
        if search_criterion and search_value:
            data = [row for row in data if search_value.lower() in str(row.get(search_criterion, '')).lower()]

    # Pagination
    page = int(request.args.get('page', 1))  # Numéro de page (défaut à 1)
    per_page = 10  # Nombre de lignes par page
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_data = data[start:end]
    total_pages = (total + per_page - 1) // per_page  # Calcul du nombre total de pages

    # Sauvegarder les modifications dans le fichier Excel
    df.to_excel(excel_file, index=False, engine='openpyxl')

    return render_template(
        'view_discipline.html',
        data=paginated_data,
        columns=columns,
        page=page,
        total_pages=total_pages,
        max=max,
        min=min
    )

@app.route('/add_discipline', methods=['GET', 'POST'])
def add_discipline():
    if request.method == 'POST':
        new_entry = {col: request.form.get(col, '') for col in DISCIPLINE_COLUMNS}
        df = pd.read_excel('data of pore app\Suivi des mesures disciplinaires.xlsx', engine='openpyxl')
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel('data of pore app\Suivi des mesures disciplinaires.xlsx', index=False, engine='openpyxl')
        log_action("Ajout d'une nouvelle mesure disciplinaire")
        flash("Enregistrement ajouté avec succès !", "success")
        return redirect(url_for('view_discipline'))
    return render_template('add_discipline.html', columns=DISCIPLINE_COLUMNS)

@app.route('/update_discipline/<int:index>', methods=['GET', 'POST'])
def update_discipline(index):
    excel_file = 'data of pore app/Suivi des mesures disciplinaires.xlsx'
    df = pd.read_excel(excel_file, engine='openpyxl')

    if request.method == 'POST':
        for col in df.columns:
            value = request.form.get(col, '')
            # Convertir les dates au format approprié, si nécessaire
            if col == 'Date' and value:
                try:
                    value = pd.to_datetime(value).strftime('%Y-%m-%d')
                except ValueError:
                    value = ''
            df.at[index, col] = value
        df.to_excel(excel_file, index=False, engine='openpyxl')
        log_action("Mise à jour d'une mesure disciplinaire")
        flash("Enregistrement mis à jour avec succès !", "success")
        return redirect(url_for('view_discipline'))

    data = df.iloc[index].to_dict()
    columns = df.columns.tolist()  # Liste des colonnes

    return render_template('update_discipline.html', index=index, data=data, columns=columns)


@app.route('/confirm_delete_discipline/<int:index>', methods=['GET', 'POST'])
def confirm_delete_discipline(index):
    if request.method == 'POST':
        excel_file = 'data of pore app\Suivi des mesures disciplinaires.xlsx'
        df = pd.read_excel(excel_file, engine='openpyxl')
        df = df.drop(index)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        log_action("Suppresion de suivi disciplinaires")
        flash("Enregistrement supprimé avec succès !", "success")
        return redirect(url_for('view_discipline'))

    excel_file = 'data of pore app\Suivi des mesures disciplinaires.xlsx'
    df = pd.read_excel(excel_file, engine='openpyxl')
    data = df.iloc[index].to_dict()
    return render_template('confirm_delete_discipline.html', data=data, columns=DISCIPLINE_COLUMNS, index=index)

@app.route('/import_discipline', methods=['GET', 'POST'])
def import_discipline():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            DISCIPLINE_COLUMNS = [
                'MAT', 'CIN', 'Emetteur', 'Violateur', 'Fonction', 'Date', 'Organisme', 'Motif de sanction 1', 'Type de sanction 1', 'Motif de sanction 2', 'Type de sanction 2', 'Motif de sanction 3', 'Type de sanction 3', 'Observations'
            ]

            # Liste des colonnes de date spécifiques à votre fichier de suivi des mesures disciplinaires
            date_columns = ['Date']

            # Déterminer le moteur en fonction de l'extension du fichier
            if file.filename.endswith('.xlsx'):
                engine = 'openpyxl'
            elif file.filename.endswith('.xls'):
                engine = 'xlrd'
            
            # Lire le nouveau fichier Excel
            df_new = pd.read_excel(file, engine=engine)
            # Lire le fichier Excel existant
            df_existing = pd.read_excel('data of pore app/Suivi des mesures disciplinaires.xlsx', engine='openpyxl')

            # Vérifier si les colonnes correspondent
            if set(df_new.columns) == set(df_existing.columns):
                # Convertir les colonnes de date en datetime
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_datetime(df_new[col], errors='coerce', dayfirst=True)
                    if col in df_existing.columns:
                        df_existing[col] = pd.to_datetime(df_existing[col], errors='coerce', dayfirst=True)

                # Remplacer les dates NaT par des valeurs vides (ou une valeur par défaut si nécessaire)
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = df_new[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')
                    if col in df_existing.columns:
                        df_existing[col] = df_existing[col].fillna('').apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if isinstance(x, pd.Timestamp) else '')

                # Combiner les DataFrames et supprimer les doublons
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates().reset_index(drop=True)
                # Enregistrer le fichier Excel combiné
                df_combined.to_excel('data of pore app/Suivi des mesures disciplinaires.xlsx', index=False, engine='openpyxl')

                flash("Fichier importé et fusionné avec succès !", "success")
                log_action("Importation de fichier mesures disciplinaires ")
            else:
                flash("Les colonnes du fichier importé ne correspondent pas au tableau existant.", "danger")
        else:
            flash("Veuillez télécharger un fichier Excel valide (.xlsx ou .xls).", "danger")

        return redirect(url_for('view_discipline'))
    
    return render_template('import_discipline.html')

discipline_excel_file = "data of pore app/Suivi des mesures disciplinaires.xlsx"
@app.route('/download/discipline_excel')
def download_discipline_excel():
    # Charger les données depuis le fichier Excel
    df = pd.read_excel(discipline_excel_file, engine='openpyxl')
    
    # Vérifier si les données sont chargées avec succès
    if not df.empty:
        # Générer le fichier Excel
        excel_filename = 'suivi_mesures_disciplinaires.xlsx'
        df.to_excel(excel_filename, index=False)
        log_action("Telechargements de mesures disciplinaires")
        # Envoyer le fichier Excel en réponse à la requête
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."


HABILITATION_COLUMNS = [
    'MAT', 'CIN', 'Nom', 'Prénom', 'Fonction', 'Type d\'habilitation', 'Motif d\'habilitation', 'Organisme',
    'Date date de délivrance 1', 'Durée de validité 1', 'Date d\'expiration 1',
    'Date date de délivrance 2', 'Durée de validité 2', 'Date d\'expiration 2',
    'Date date de délivrance 3', 'Durée de validité 3', 'Date d\'expiration 3',
    'Observations'
]

habilitation_excel_file = "data of pore app\Habilitation.xlsx"

@app.route('/download/habilitation_excel')
def download_habilitation_excel():
    df = pd.read_excel(habilitation_excel_file, engine='openpyxl')
    
    if not df.empty:
        excel_filename = 'suivi_habilitations.xlsx'
        df.to_excel(excel_filename, index=False)
        log_action("Telechargement de fichier habilitation")
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."

@app.route('/view_habilitation', methods=['GET', 'POST'])
def view_habilitation():
    habilitation_excel_file = 'data of pore app\Habilitation.xlsx'  # Assurez-vous que cette variable est définie correctement
    df = pd.read_excel(habilitation_excel_file, engine='openpyxl')

    date_columns = [
        'Date date de délivrance 1', 'Date d\'expiration 1',
        'Date date de délivrance 2', 'Date d\'expiration 2',
        'Date date de délivrance 3', 'Date d\'expiration 3'
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: '' if pd.isna(x) else x.strftime('%Y-%m-%d'))

    columns = df.columns.tolist()
    data = df.to_dict(orient='records')

    if request.method == 'POST':
        search_criterion = request.form.get('search_criterion')
        search_value = request.form.get('search_value')
        if search_criterion and search_value:
            data = [row for row in data if search_value.lower() in str(row.get(search_criterion, '')).lower()]

    # Pagination
    page = int(request.args.get('page', 1))  # Numéro de page (défaut à 1)
    per_page = 10  # Nombre de lignes par page
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_data = data[start:end]
    total_pages = (total + per_page - 1) // per_page  # Calcul du nombre total de pages

    df.to_excel(habilitation_excel_file, index=False, engine='openpyxl')

    return render_template(
        'view_habilitation.html',
        data=paginated_data,
        columns=columns,
        page=page,
        total_pages=total_pages,
        max=max,
        min=min
    )

@app.route('/add_habilitation', methods=['GET', 'POST'])
def add_habilitation():
    if request.method == 'POST':
        new_entry = {col: request.form.get(col, '') for col in HABILITATION_COLUMNS}
        df = pd.read_excel(habilitation_excel_file, engine='openpyxl')
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel(habilitation_excel_file, index=False, engine='openpyxl')
        log_action("Ajout nouveau habilitation")
        flash("Enregistrement ajouté avec succès !", "success")
        return redirect(url_for('view_habilitation'))
    return render_template('add_habilitation.html', columns=HABILITATION_COLUMNS)


@app.route('/update_habilitation/<int:index>', methods=['GET', 'POST'])
def update_habilitation(index):
    df = pd.read_excel(habilitation_excel_file, engine='openpyxl')

    if request.method == 'POST':
        for col in HABILITATION_COLUMNS:
            df.at[index, col] = request.form.get(col, '')
        df.to_excel(habilitation_excel_file, index=False, engine='openpyxl')
        flash("Enregistrement mis à jour avec succès !", "success")
        log_action("Mise à jour d'une habilitation")
        return redirect(url_for('view_habilitation'))

    data = df.iloc[index].to_dict()
    return render_template('update_habilitation.html', index=index, data=data, columns=HABILITATION_COLUMNS)

@app.route('/confirm_delete_habilitation/<int:index>', methods=['GET', 'POST'])
def confirm_delete_habilitation(index):
    if request.method == 'POST':
        df = pd.read_excel(habilitation_excel_file, engine='openpyxl')
        df = df.drop(index)
        df.to_excel(habilitation_excel_file, index=False, engine='openpyxl')
        flash("Enregistrement supprimé avec succès !", "success")
        log_action("Suppresion d'une habilitation")
        return redirect(url_for('view_habilitation'))

    df = pd.read_excel(habilitation_excel_file, engine='openpyxl')
    data = df.iloc[index].to_dict()
    return render_template('confirm_delete_habilitation.html', data=data, columns=HABILITATION_COLUMNS, index=index)


@app.route('/import_habilitation', methods=['GET', 'POST'])
def import_habilitation():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            # Liste des colonnes de date
            date_columns = [
                'Date date de délivrance 1', 'Date d\'expiration 1',
                'Date date de délivrance 2', 'Date d\'expiration 2',
                'Date date de délivrance 3', 'Date d\'expiration 3'
            ]

            # Déterminer le moteur en fonction de l'extension du fichier
            if file.filename.endswith('.xlsx'):
                engine = 'openpyxl'
            elif file.filename.endswith('.xls'):
                engine = 'xlrd'
            
            # Lire le nouveau fichier Excel
            df_new = pd.read_excel(file, engine=engine)
            # Lire le fichier Excel existant
            df_existing = pd.read_excel('data of pore app/Habilitation.xlsx', engine='openpyxl')

            # Vérifier si les colonnes correspondent
            if set(df_new.columns) == set(df_existing.columns):
                # Convertir les colonnes de date en datetime
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_datetime(df_new[col], errors='coerce', dayfirst=True)
                    if col in df_existing.columns:
                        df_existing[col] = pd.to_datetime(df_existing[col], errors='coerce', dayfirst=True)

                # Remplacer les dates NaT par des valeurs vides
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = df_new[col].fillna('').apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else '')
                    if col in df_existing.columns:
                        df_existing[col] = df_existing[col].fillna('').apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else '')

                # Combiner les DataFrames et supprimer les doublons
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates().reset_index(drop=True)
                # Enregistrer le fichier Excel combiné
                df_combined.to_excel('data of pore app/Habilitation.xlsx', index=False, engine='openpyxl')
                log_action("Importations nouveaux habilitations")
                flash("Fichier importé et fusionné avec succès !", "success")
            else:
                flash("Les colonnes du fichier importé ne correspondent pas au tableau existant.", "danger")
        else:
            flash("Veuillez télécharger un fichier Excel valide (.xlsx ou .xls).", "danger")

        return redirect(url_for('view_habilitation'))
    
    return render_template('import_habilitation.html')


# Configuration des colonnes et du chemin de fichier pour les visites médicales
VISITE_MEDICALE_COLUMNS = [
    'MAT', 'NOM PRENOM', 'FONCTION', 'CIN', 'CNSS', 'DATE DE NAISSANCE', 'DATE D\'EMBAUCHE',
    'Certificat d\'aptitude physique d\'embauche', 'Observations', 'DATE DERNIÈRE VISITE',
    'Date Viste programmée', 'Observations', 'Date de visite médicale 2', 'Observations', 'Observations générales'
]
visite_medicale_excel_file = "data of pore app\Suivi-des-visites-médicales.xlsx"

@app.route('/download/visite_medicale_excel')
def download_visite_medicale_excel():
    df = pd.read_excel(visite_medicale_excel_file, engine='openpyxl')
    if not df.empty:
        excel_filename = 'suivi_visites_medicales.xlsx'
        df.to_excel(excel_filename, index=False)
        log_action("Telechargement de fichier de visites medicales")
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."

@app.route('/view_visite_medicale', methods=['GET', 'POST'])
def view_visite_medicale():
    visite_medicale_excel_file = 'data of pore app\Suivi-des-visites-médicales.xlsx'
    df = pd.read_excel(visite_medicale_excel_file, engine='openpyxl')

    # Nettoyer les colonnes en supprimant les espaces supplémentaires
    df.columns = df.columns.str.strip()
    # Convertir le matricule en string
    df['MAT'] = df['MAT'].astype(str)  # Remplacez 'MAT' par le nom exact de votre colonne


    # Vérifier s'il y a des colonnes en double
    duplicates = df.columns[df.columns.duplicated()]
    if not duplicates.empty:
        print(f"Doublons trouvés dans les colonnes: {list(duplicates)}")
        df = df.loc[:, ~df.columns.duplicated()]  # Supprime les doublons de colonnes

    # Colonnes contenant des dates
    date_columns = [
        'DATE DE NAISSANCE', 'DATE D\'EMBAUCHE', 
        'DATE DERNIÈRE VISITE', 'Date Viste programmée', 
        'Date de visite médicale 2'
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: '' if pd.isna(x) else x.strftime('%Y-%m-%d'))
        else:
            print(f"La colonne {col} n'existe pas dans le fichier Excel.")

    columns = df.columns.tolist()
    data = df.to_dict(orient='records')

    if request.method == 'POST':
        search_criterion = request.form.get('search_criterion')
        search_value = request.form.get('search_value')
        if search_criterion and search_value:
            data = [row for row in data if search_value.lower() in str(row.get(search_criterion, '')).lower()]

    # Pagination
    page = int(request.args.get('page', 1))  # Numéro de page (défaut à 1)
    per_page = 10  # Nombre de lignes par page
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_data = data[start:end]
    total_pages = (total + per_page - 1) // per_page  # Calcul du nombre total de pages

    return render_template(
        'view_visite_medicale.html',
        data=paginated_data,
        columns=columns,
        page=page,
        total_pages=total_pages,
        max=max,
        min=min
    )

@app.route('/add_visite_medicale', methods=['GET', 'POST'])
def add_visite_medicale():
    if request.method == 'POST':
        new_entry = {col: request.form.get(col, '') for col in VISITE_MEDICALE_COLUMNS}
        df = pd.read_excel(visite_medicale_excel_file, engine='openpyxl')
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel(visite_medicale_excel_file, index=False, engine='openpyxl')
        log_action("Ajour d'une nouvelle visite médicale")
        flash("Enregistrement ajouté avec succès !", "success")
        return redirect(url_for('view_visite_medicale'))
    return render_template('add_visite_medicale.html', columns=VISITE_MEDICALE_COLUMNS)

@app.route('/update_visite_medicale/<int:index>', methods=['GET', 'POST'])
def update_visite_medicale(index):
    df = pd.read_excel(visite_medicale_excel_file, engine='openpyxl')
    if request.method == 'POST':
        for col in VISITE_MEDICALE_COLUMNS:
            df.at[index, col] = request.form.get(col, '')
        df.to_excel(visite_medicale_excel_file, index=False, engine='openpyxl')
        flash("Enregistrement mis à jour avec succès !", "success")
        log_action("Mise à jour d'une visite médicales")
        return redirect(url_for('view_visite_medicale'))
    data = df.iloc[index].to_dict()
    return render_template('update_visite_medicale.html', index=index, data=data, columns=VISITE_MEDICALE_COLUMNS)

@app.route('/confirm_delete_visite_medicale/<int:index>', methods=['GET', 'POST'])
def confirm_delete_visite_medicale(index):
    if request.method == 'POST':
        df = pd.read_excel(visite_medicale_excel_file, engine='openpyxl')
        df = df.drop(index)
        df.to_excel(visite_medicale_excel_file, index=False, engine='openpyxl')
        flash("Enregistrement supprimé avec succès !", "success")
        log_action("Suppresion d'une visiste medicale")
        return redirect(url_for('view_visite_medicale'))
    df = pd.read_excel(visite_medicale_excel_file, engine='openpyxl')
    data = df.iloc[index].to_dict()
    return render_template('confirm_delete_visite_medicale.html', data=data, columns=VISITE_MEDICALE_COLUMNS, index=index)

@app.route('/import_visite_medicale', methods=['GET', 'POST'])
def import_visite_medicale():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            date_columns = ['DATE DE NAISSANCE', 'DATE D\'EMBAUCHE', 'DATE DERNIÈRE VISITE', 'Date Viste programmée', 'Date de visite médicale 2']
            if file.filename.endswith('.xlsx'):
                engine = 'openpyxl'
            elif file.filename.endswith('.xls'):
                engine = 'xlrd'
            
            df_new = pd.read_excel(file, engine=engine)
            df_existing = pd.read_excel(visite_medicale_excel_file, engine='openpyxl')

            if set(df_new.columns) == set(df_existing.columns):
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_datetime(df_new[col], errors='coerce', dayfirst=True)
                    if col in df_existing.columns:
                        df_existing[col] = pd.to_datetime(df_existing[col], errors='coerce', dayfirst=True)

                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = df_new[col].fillna('').apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else '')
                    if col in df_existing.columns:
                        df_existing[col] = df_existing[col].fillna('').apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else '')

                df_combined = pd.concat([df_existing, df_new]).drop_duplicates().reset_index(drop=True)
                df_combined.to_excel(visite_medicale_excel_file, index=False, engine='openpyxl')
                log_action("Importation de visites medicales")
                flash("Fichier importé et fusionné avec succès !", "success")
            else:
                flash("Les colonnes du fichier importé ne correspondent pas au tableau existant.", "danger")
        else:
            flash("Veuillez télécharger un fichier Excel valide (.xlsx ou .xls).", "danger")

        return redirect(url_for('view_visite_medicale'))
    
    return render_template('import_visite_medicale.html')




# Chemin vers le fichier Excel
excel_file = "data of pore app/Registre du suivi des actions disciplinaires.xlsx"



# Définition de la fonction pour charger les données Excel
def load_excel(filename):
    try:
        df = pd.read_excel(filename)
        return df
    except Exception as e:
        print(f"Erreur lors du chargement du fichier Excel : {str(e)}")
        return None

@app.route('/download/excel')
def download_excel():
    # Charger les données depuis le fichier Excel en utilisant load_excel
    df = load_excel(excel_file)
    
    # Vérifier si les données sont chargées avec succès
    if df is not None and not df.empty:
        # Générer le fichier Excel
        excel_filename = 'registre_actions_disciplinaires.xlsx'
        df.to_excel(excel_filename, index=False)
        log_action("Telechargement de fichier des sanctions")
        # Envoyer le fichier Excel en réponse à la requête
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."



# Chemin vers le fichier Excel
epi_excel_file = "data of pore app/Suivi de Remise des EPI Finale.xlsx"
@app.route('/download/epi_excel')
def download_epi_excel():
    # Charger les données depuis le fichier Excel en utilisant load_excel
    df = load_excel(epi_excel_file)
    
    # Vérifier si les données sont chargées avec succès
    if df is not None and not df.empty:
        # Générer le fichier Excel
        excel_filename = 'suivi_remise_epi.xlsx'
        df.to_excel(excel_filename, index=False)
        
        # Envoyer le fichier Excel en réponse à la requête
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."
    
# Chemin vers le fichier Excel pour le suivi des EPI 1
epi1_excel_file = "data of pore app/suivi de remise des EPI 1.xlsx"

@app.route('/download/epi1_excel')
def download_epi1_excel():
    # Charger les données depuis le fichier Excel en utilisant load_excel
    df = load_excel(epi1_excel_file)
    
    # Vérifier si les données sont chargées avec succès
    if df is not None and not df.empty:
        # Générer le fichier Excel
        excel_filename = 'suivi_remise_epi1.xlsx'
        df.to_excel(excel_filename, index=False)
        
        # Envoyer le fichier Excel en réponse à la requête
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."

# Chemin vers le fichier Excel pour la fiche de formation finale
formation_excel_file = "data of pore app/fiche formation finale.xlsx"

@app.route('/download/formation_excel')
def download_formation_excel():
    # Charger les données depuis le fichier Excel en utilisant load_excel
    df = load_excel(formation_excel_file)
    
    # Vérifier si les données sont chargées avec succès
    if df is not None and not df.empty:
        # Générer le fichier Excel
        excel_filename = 'fiche_formation_finale.xlsx'
        df.to_excel(excel_filename, index=False)
        
        # Envoyer le fichier Excel en réponse à la requête
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."

# Chemin vers le fichier Excel pour la fiche de formation finale
sens_excel_file = "data of pore app\Gestion des sensibilisation (1).xlsx"

@app.route('/download/sens_excel')
def download_sens_excel():
    # Charger les données depuis le fichier Excel en utilisant load_excel
    df = load_excel(sens_excel_file)
    
    # Vérifier si les données sont chargées avec succès
    if df is not None and not df.empty:
        # Générer le fichier Excel
        excel_filename = 'fiche_sensibilisation_finale.xlsx'
        df.to_excel(excel_filename, index=False)
        
        # Envoyer le fichier Excel en réponse à la requête
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."



@app.route('/upload_epi_excel', methods=['POST'])
def upload_epi_excel():
    if 'excel_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('view_epi'))

    file = request.files['excel_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('view_epi'))

    if file and file.filename.endswith('.xlsx'):
        new_df = pd.read_excel(file, engine='openpyxl')

        # List of date columns
        date_columns = ['D EMBAUCHE', 'Date récharge EPI', 'Casque: date de remise', 'Chaussures: date de remise',
                        'Gants: date de remise', 'Gilet fluoreçant: date de remise', 'Combinaison imperméable: date de remise',
                        'Lunettes (Anti-poussière ): date de remise', 'Bote de sécurité: date de remise',
                        'Gilet de sauvetage: date de remise', 'Autre: date de remise']

        # Debug: Print initial date values and identify problems
        for col in date_columns:
            if col in new_df.columns:
                print(f"Initial values - {col}:")
                print(new_df[col].head(10))  # Print more rows for better visibility

        # Convert date columns to datetime using multiple formats
        for col in date_columns:
            if col in new_df.columns:
                new_df[col] = pd.to_datetime(new_df[col], errors='coerce', dayfirst=True)

        # Debug: Print converted date values
        for col in date_columns:
            if col in new_df.columns:
                print(f"Converted values - {col}:")
                print(new_df[col].head(10))

        # Format dates to 'dd/mm/yyyy'
        for col in date_columns:
            if col in new_df.columns:
                new_df[col] = new_df[col].dt.strftime('%d/%m/%Y')

        existing_df = pd.read_excel(EPI_FILE, engine='openpyxl')
        
        # Check if columns match
        if not new_df.columns.equals(existing_df.columns):
            flash('Les colonnes du fichier importé ne correspondent pas aux colonnes du tableau existant.', 'danger')
            return redirect(url_for('view_epi'))

        # Find new rows
        combined_df = pd.concat([existing_df, new_df]).drop_duplicates(keep=False)
        
        if not combined_df.empty:
            # Append new rows to existing file
            updated_df = pd.concat([existing_df, combined_df])
            updated_df.to_excel(EPI_FILE, index=False, engine='openpyxl')
            log_action("Importations EPIs ")
            flash('Les nouvelles données ont été ajoutées avec succès.', 'success')
        else:
            flash('Aucune nouvelle donnée à ajouter.', 'info')
    else:
        flash('Fichier invalide. Veuillez télécharger un fichier Excel (.xlsx).', 'danger')

    return redirect(url_for('view_epi'))


# Chemin vers le fichier Excel pour les accidents de travail
accident_excel_file = "data of pore app/Accident de travail.xlsx"
@app.route('/download/acc_excel')
def download_acc_excel():
    # Charger les données depuis le fichier Excel en utilisant load_excel
    df = load_excel(accident_excel_file)
    
    # Vérifier si les données sont chargées avec succès
    if df is not None and not df.empty:
        # Générer le fichier Excel à partir des données chargées
        excel_filename = 'fiche_accident_de_travail.xlsx'
        df.to_excel(excel_filename, index=False)
        
        # Envoyer le fichier Excel en réponse à la requête
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."

# Configuration des colonnes et du chemin de fichier pour les récompenses
RECOMPENSE_COLUMNS = [
    'MAT', 'CIN', 'Nom', 'Prenom', 'Fonction', 'Affectation', 'Date', 'Type de récompense', 
    'Motif de récompense', 'Observations'
]
recompense_excel_file = "data of pore app/Systeme de recompense.xlsx"

@app.route('/download/recompense_excel')
def download_recompense_excel():
    df = pd.read_excel(recompense_excel_file, engine='openpyxl')
    if not df.empty:
        excel_filename = 'systeme_recompenses.xlsx'
        df.to_excel(excel_filename, index=False)
        return send_file(excel_filename, as_attachment=True)
    else:
        return "Aucune donnée disponible dans le fichier Excel."

@app.route('/view_recompense', methods=['GET', 'POST'])
def view_recompense():
    df = pd.read_excel(recompense_excel_file, engine='openpyxl')

    # Nettoyer les colonnes en supprimant les espaces supplémentaires
    df.columns = df.columns.str.strip()
    df['MAT'] = df['MAT'].astype(str)  # Assurez-vous que 'MAT' est bien le nom exact de votre colonne

    # Vérifier s'il y a des colonnes en double
    duplicates = df.columns[df.columns.duplicated()]
    if not duplicates.empty:
        print(f"Doublons trouvés dans les colonnes: {list(duplicates)}")
        df = df.loc[:, ~df.columns.duplicated()]  # Supprime les doublons de colonnes

    # Colonnes contenant des dates
    date_columns = ['Date']

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: '' if pd.isna(x) else x.strftime('%Y-%m-%d'))
        else:
            print(f"La colonne {col} n'existe pas dans le fichier Excel.")

    columns = df.columns.tolist()
    data = df.to_dict(orient='records')

    if request.method == 'POST':
        search_criterion = request.form.get('search_criterion')
        search_value = request.form.get('search_value')
        if search_criterion and search_value:
            data = [row for row in data if search_value.lower() in str(row.get(search_criterion, '')).lower()]

    # Pagination
    page = int(request.args.get('page', 1))  # Numéro de page (défaut à 1)
    per_page = 10  # Nombre de lignes par page
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_data = data[start:end]
    total_pages = (total + per_page - 1) // per_page  # Calcul du nombre total de pages

    return render_template(
        'view_recompense.html',
        data=paginated_data,
        columns=columns,
        page=page,
        total_pages=total_pages,
        max=max,
        min=min
    )

@app.route('/add_recompense', methods=['GET', 'POST'])
def add_recompense():
    if request.method == 'POST':
        new_entry = {col: request.form.get(col, '') for col in RECOMPENSE_COLUMNS}
        df = pd.read_excel(recompense_excel_file, engine='openpyxl')
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel(recompense_excel_file, index=False, engine='openpyxl')
        log_action("Ajout de nouvel recompense")
        flash("Enregistrement ajouté avec succès !", "success")
        return redirect(url_for('view_recompense'))
    return render_template('add_recompense.html', columns=RECOMPENSE_COLUMNS)

@app.route('/update_recompense/<int:index>', methods=['GET', 'POST'])
def update_recompense(index):
    df = pd.read_excel(recompense_excel_file, engine='openpyxl')
    if request.method == 'POST':
        for col in RECOMPENSE_COLUMNS:
            df.at[index, col] = request.form.get(col, '')
        df.to_excel(recompense_excel_file, index=False, engine='openpyxl')
        log_action("Mise à jour de recompense")
        flash("Enregistrement mis à jour avec succès !", "success")
        return redirect(url_for('view_recompense'))
    data = df.iloc[index].to_dict()
    return render_template('update_recompense.html', index=index, data=data, columns=RECOMPENSE_COLUMNS)

@app.route('/confirm_delete_recompense/<int:index>', methods=['GET', 'POST'])
def confirm_delete_recompense(index):
    if request.method == 'POST':
        df = pd.read_excel(recompense_excel_file, engine='openpyxl')
        df = df.drop(index)
        df.to_excel(recompense_excel_file, index=False, engine='openpyxl')
        log_action("Suppresion d'une recompense")
        flash("Enregistrement supprimé avec succès !", "success")
        return redirect(url_for('view_recompense'))
    df = pd.read_excel(recompense_excel_file, engine='openpyxl')
    data = df.iloc[index].to_dict()
    return render_template('confirm_delete_recompense.html', data=data, columns=RECOMPENSE_COLUMNS, index=index)

@app.route('/import_recompense', methods=['GET', 'POST'])
def import_recompense():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            date_columns = ['Date']
            if file.filename.endswith('.xlsx'):
                engine = 'openpyxl'
            elif file.filename.endswith('.xls'):
                engine = 'xlrd'
            
            df_new = pd.read_excel(file, engine=engine)
            df_existing = pd.read_excel(recompense_excel_file, engine='openpyxl')

            if set(df_new.columns) == set(df_existing.columns):
                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_datetime(df_new[col], errors='coerce', dayfirst=True)
                    if col in df_existing.columns:
                        df_existing[col] = pd.to_datetime(df_existing[col], errors='coerce', dayfirst=True)

                for col in date_columns:
                    if col in df_new.columns:
                        df_new[col] = df_new[col].fillna('').apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else '')
                    if col in df_existing.columns:
                        df_existing[col] = df_existing[col].fillna('').apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else '')

                df_combined = pd.concat([df_existing, df_new]).drop_duplicates().reset_index(drop=True)
                df_combined.to_excel(recompense_excel_file, index=False, engine='openpyxl')
                log_action("Importation de nouveau recompense")
                flash("Fichier importé et fusionné avec succès !", "success")
            else:
                flash("Les colonnes du fichier importé ne correspondent pas au tableau existant.", "danger")
        else:
            flash("Veuillez télécharger un fichier Excel valide (.xlsx ou .xls).", "danger")

        return redirect(url_for('view_recompense'))
    
    return render_template('import_recompense.html')



import re

# Fonction pour extraire les nombres des chaînes de caractères
def extract_number_from_string(s):
    if pd.notna(s):
        match = re.search(r'\d+', str(s))
        if match:
            return int(match.group())
    return 0

# Chemins vers les fichiers Excel
EPI_FILE = 'data of pore app/suivi de remise des EPI Finale.xlsx'
FORMATION_FILE = 'data of pore app/fiche formation finale.xlsx'
SENS_FILE = 'data of pore app/Gestion des sensibilisation (1).xlsx'
DISCIPLINARY_FILE = 'data of pore app/Registre du suivi des actions disciplinaires.xlsx'
ACCIDENT_FILE = 'data of pore app/Accident de travail.xlsx'
HABILITATION_FILE = 'data of pore app/Habilitation.xlsx'
DISCIPLINE_FILE = 'data of pore app/Suivi des mesures disciplinaires.xlsx'
VISITE_MEDICALE_FILE = 'data of pore app/Suivi-des-visites-médicales.xlsx'

# Charger les fichiers Excel
dataframes = {}

file_paths = {
    'epi': EPI_FILE,
    'formation': FORMATION_FILE,
    'sens': SENS_FILE,
    'disciplinary': DISCIPLINARY_FILE,
    'accident': ACCIDENT_FILE,
    'habilitation': HABILITATION_FILE,
    'discipline' : DISCIPLINE_FILE,
    'visite_medicale': VISITE_MEDICALE_FILE 
}

for key, path in file_paths.items():
    try:
        df = pd.read_excel(path, engine='openpyxl')
        df['MAT'] = df['MAT'].astype(str)  # Convertir MAT en string
        #df['CIN'] = df['CIN'].astype(str)  # Convertir CIN en string
        dataframes[key] = df
        print(f"{key.upper()} loaded successfully.")
    except Exception as e:
        print(f"Error loading {key.upper()}: {e}")


# Fonction pour obtenir les informations de l'employé
def get_employee_info(mat):
    columns_to_display = ['AFFECTATION', 'NOM ET PRENOM', 'CIN', 'D EMBAUCHE', 'Date récharge EPI', 'SITE']
    epi_details_columns = [
        'Casque: Nombre', 'Casque: Taille/type', 'Casque: date de remise',
        'Chaussures: Nombre', 'Chaussures: Taille/type', 'Chaussures: date de remise',
        'Gants: Nombre', 'Gants: Taille/type', 'Gants: date de remise',
        'Gilet fluoreçant: Nombre', 'Gilet fluoreçant: Taille/type', 'Gilet fluoreçant: date de remise',
        'Combinaison imperméable: Nombre', 'Combinaison imperméable: Taille/type', 'Combinaison imperméable: date de remise',
        'Lunettes (Anti-poussière ): Nombre', 'Lunettes (Anti-poussière ): Taille/type', 'Lunettes (Anti-poussière ): date de remise',
        'Bote de sécurité: Nombre', 'Bote de sécurité: Taille/type', 'Bote de sécurité: date de remise',
        'Gilet de sauvetage: Nombre', 'Gilet de sauvetage: Taille/type', 'Gilet de sauvetage: date de remise',
        'Autre: Nombre', 'Autre: Taille/type', 'Autre: date de remise'
    ]

    sens_details_columns = [
         'AFFEECTATION', 'MAT', 'NOM ET PRENOM', 'FONCTION', 'CIN', 'D EMBAUCHE', 'SECTION',
    'Sensibilisation sur des travaux en hateur: Nombre', 'Sensibilisation sur des travaux en hateur: Date',
    'Sensibilisation sur les techniques d\'ingage: Nombre', 'Sensibilisation sur les techniques d\'ingage: Date',
    'Sensibilisation sur les risques des maladiers professionnelle et les prévention à prendre au cours de travail : Nombre',
    'Sensibilisation sur les risques des maladiers professionnelle et les prévention à prendre au cours de travail : Date',
    'Sensibilisation sur les précontions à pendant les travaux de soudage: Nombre',
    'Sensibilisation sur les précontions à pendant les travaux de soudage: Date',
    'Sensibilisation sur les risques de chut et de glissade l\'ies aux déplacements : Nombre',
    'Sensibilisation sur les risques de chut et de glissade l\'ies aux déplacements : Date',
    'Sensibilisation sur les risques électriques: Nombre', 'Sensibilisation sur les risques électriques: Date',
    'sensibilisation sur l\'importance de mettre l\'etiquatage des produits chimiques: Nombre',
    'sensibilisation sur l\'importance de mettre l\'etiquatage des produits chimiques: Date',
    'sensibilisation sur les gestes et postures au travail: Nombre', 'sensibilisation sur les gestes et postures au travail: Date',
    'senisibilisation sur les risques lieé a l\'activité physique de travail (maneutation manuelle): Nombre',
    'senisibilisation sur les risques lieé a l\'activité physique de travail (maneutation manuelle): Date',
    'Sensibilisation sur les risque covid: Nombre', 'Sensibilisation sur les risque covid: Date',
    'Sensibilisation sur les risques lieé au travaux de décharge et charge des barres de ferraillage: Nombre',
    'Sensibilisation sur les risques lieé au travaux de décharge et charge des barres de ferraillage: Date',
    'Sensibilisation incedie: Nombre', 'Sensibilisation incedie: Date',
    'Sensibilisation sur les risques lieés au travail à proximité d\'un pelle pour eviter les écrassements: Nombre',
    'Sensibilisation sur les risques lieés au travail à proximité d\'un pelle pour eviter les écrassements: Date',
    'Sensibilisation sur équipements mobiles et circulation: nombre', 'Sensibilisation sur équipements mobiles et circulation : Date',
    'Sensibilisation sur les travaux à proximité de l\'eaux / la mer: Nombre', 'Sensibilisation sur les travaux à proximité de l\'eaux / la mer: Date',
    'Sensibilisation sur les risques environnemtaux (nettoyage): Nombre', 'Sensibilisation sur les risques environnemtaux (nettoyage): Date',
    'Sensibilisation sur les travaux de sablage pour éviter les accidents: Nombre', 'Sensibilisation sur les travaux de sablage pour éviter les accidents: Date',
    'Sensibilisation sur risques lieés aux operation de levage: Nombre', 'Sensibilisation sur risques lieés aux operation de levage: Date',
    'Sensibilisation sur l\'obligation de coordination avec le serviece HSE avent de procéder aux operations critiques: Nombre',
    'Sensibilisation sur l\'obligation de coordination avec le serviece HSE avent de procéder aux operations critiques: Date',
    'Sensibilisation sur les risques de chate et de glissade l\'iees aux déplacement: Nombre',
    'Sensibilisation sur les risques de chate et de glissade l\'iees aux déplacement : Date'
    ]

    formation_details_columns = [
          'AFFEECTATION', 'MAT', 'NOM ET PRENOM', 'FONCTION', 'CIN', 'D EMBAUCHE', 'SECTION',
    'Formation sur prévention des risques électriques: Nombre', 'Formation sur prévention des risques électriques: Date',
    'Formation sur les techniques d\'elingage en sécurité: Nombre', 'Formation sur les techniques d\'elingage en sécurité: Date',
    'Formation sur les travaux en hauteur: Nombre', 'Formation sur les travaux en hauteur: Date',
    'Formation sur les travaux offshores: Nombre', 'Formation sur les travaux offshores: Date',
    'Formation sur des signaleurs: Nombre', 'Formation sur des signaleurs: Date',
    'Formation sur la conduite en sécurité sur chantier: Nombre', 'Formation sur la conduite en sécurité sur chantier: Date',
    'Formation sur les équipements mobiles et circulation: Nombre', 'Formation sur les équipements mobiles et circulation: Date',
    'Formation sur l\'usage sécuritaire de l\'échafaudage: Nombre', 'Formation sur l\'usage sécuritaire de l\'échafaudage: Date',
    'Formation sur le respect du 5S: Nombre', 'Formation sur le respect du 5S: Date',
    'Formation sur la necessité du vigilence et port des EPI: Nombre', 'Formation sur la necessité du vigilence et port des EPI: Date',
    'Formation sur la prévention des risques des travaux maritimes: Nombre', 'Formation sur la prévention des risques des travaux maritimes: Date',
    'Formation sur les travaux à proximité de l\'eau / la mer: Nombre', 'Formation sur les travaux à proximité de l\'eau / la mer: Date',
    'Formation sur la prévention les risques des travaux ferraillage: Nombre', 'Formation sur la prévention les risques des travaux ferraillage: Date',
    'Formation sur l\'intervention sécuritaire en espace confiné: Nombre', 'Formation sur l\'intervention sécuritaire en espace confiné: Date',
    'Formation sur la consignation-déconsignation: Nombre', 'Formation sur la consignation-déconsignation: Date',
    'Formation sur les risques liés aux opération de levage: Nombre', 'Formation sur les risques liés aux opération de levage: Date',
    'Formation sur le sauvetage-secourisme au travail: Nombre', 'Formation sur le sauvetage-secourisme au travail: Date',
    'Formation sur la prévention des risques liées au chargement et déchargement des tubes métallique: Nombre', 'Formation sur la prévention des risques liées au chargement et déchargement des tubes métallique: Date',
    'Formation sur l\'usage sécuritaire des appareils électroportatifs.(HILTI): Nombre', 'Formation sur l\'usage sécuritaire des appareils électroportatifs.(HILTI): Date',
    'Formation sur les risques du démontage de la structure méttalique: Nombre', 'Formation sur les risques du démontage de la structure méttalique: Date',
    'Formation incendie: Nombre', 'Formation incendie: Date',
    'Formation sur les gestes du guidages: Nombre', 'Formation sur les gestes du guidages: Date',
    'Formation sur prévention de noyad: Nombre', 'Formation sur prévention de noyad: Date',
    'Formation sur la gestion du stress au travail: Nombre', 'Formation sur la gestion du stress au travail: Date',
    'Formation sur les risques liés au démontage de la charpente métallique: Nombre', 'Formation sur les risques liés au démontage de la charpente métallique: Date',
    'Formation sur l\'inspection des amoires électrique: Nombre', 'Formation sur l\'inspection des amoires électrique: Date',
    'Formation sur procédure de plongée: Nombre', 'Formation sur procédure de plongée: Date',
    'Techniques d\'élingage-désélingage / mantaention manuelle PRATIQUE: Nombre', 'Techniques d\'élingage-désélingage / mantaention manuelle PRATIQUE: Date',
    'Formation sur les gestes et postures: Nombre', 'Formation sur les gestes et postures: Date',
    'Formation sur les gestes et postures PRATIQUE: Nombre', 'Formation sur les gestes et postures PRATIQUE: Date',
    'formation sur eagle eyes: Nombre', 'formation sur eagle eyes: Date',
    'Formation sur la gestion des déchets: Nombre', 'Formation sur la gestion des déchets: Date',
    'Formation sur la conduite à tenir en cas de déversement accidentel: Nombre', 'Formation sur la conduite à tenir en cas de déversement accidentel: Date',
    'Formation sur la conduite à tenir en cas de déversement accidentel /PRATIQUE/: Nombre', 'Formation sur la conduite à tenir en cas de déversement accidentel /PRATIQUE/: Date',
    'Formation sur incidents environnementaux: Nombre', 'Formation sur incidents environnementaux: Date',
    'Formation sur les risques environnementaux: Nombre', 'Formation sur les risques environnementaux: Date',
    'Formation les risqus des poussiéres: Nombre', 'Formation les risqus des poussiéres: Date',
    'Formation sur produits chimiques et pictogrammes de dangers: Nombre', 'Formation sur produits chimiques et pictogrammes de dangers: Date',
    'Formation sur la procédure de gestion des matiéres dangereuses: Nombre', 'Formation sur la procédure de gestion des matiéres dangereuses: Date',
    'Formation sur gestes et postures au travail - manutention manvelle: Nombre', 'Formation sur gestes et postures au travail - manutention manvelle: Date',
    'Formation sur l\'usage de bouée sauvetage: Nombre', 'Formation sur l\'usage de bouée sauvetage: Date',
    'Formation sur les équipements mobiles et circulation-la conduite en sécurite sur chantier(CHAUFFEUR): Nombre', 'Formation sur les équipements mobiles et circulation-la conduite en sécurite sur chantier(CHAUFFEUR): Date',
    'Formation sur les risques liés aux travaux de sablage: Nombre', 'Formation sur les risques liés aux travaux de sablage: Date',
    'Formation de sécourisme au travail: Nombre', 'Formation de sécourisme au travail: Date',
    'Formation sur les mettodes et techniques utilisation des accesoires de sauvetage: Nombre', 'Formation sur les mettodes et techniques utilisation des accesoires de sauvetage: Date',
    'Formation sur l\'usage sécuritaire des appareils électroportatifs: Nombre', 'Formation sur l\'usage sécuritaire des appareils électroportatifs: Date',
    'Formation sur l\'usage sécuritaire de l\'échafaudage: Nombre', 'Formation sur l\'usage sécuritaire de l\'échafaudage: Date',
    'Formation sur l\'inspection des amoires électrique: Nombre.1', 'Formation sur l\'inspection des amoires électrique: Date.1',
    'Formation sur l\'inspection des amoires électrique: Nombre.2', 'Formation sur l\'inspection des amoires électrique: Date.2',
    'Formation sur mesures de sécurité: équipage mobile- démarrage TCO: Nombre', 'Formation sur mesures de sécurité: équipage mobile- démarrage TCO: Date',
    'Formation sur les risques et méthodes de prevention liees au travaux d\'amarrage et traction par treuil: Nombre', 'Formation sur les risques et méthodes de prevention liees au travaux d\'amarrage et traction par treuil: Date',
    'Formation sur inspection et usage du gilet de sauvetage : Nombre', 'Formation sur inspection et usage du gilet de sauvetage : Date',
    'Formation sur les techniques d\'embarquement et debarquement: Nombre', 'Formation sur les techniques d\'embarquement et debarquement: Date',
    'Formation sur la prevention des risques liés à l\'exposition au bruit: Nombre', 'Formation sur la prevention des risques liés à l\'exposition au bruit: Date',
    'Formation sur les risques existant à la CAB : nombre', 'Formation sur les risques existant à la CAB : Date',
    'Formation sur le sauvetage-secourisme au travail.(C R ): Nombre', 'Formation sur le sauvetage-secourisme au travail.(C R ): Date',
    'Formation sur equipements de sauvetage maritimes: Nombre', 'Formation sur equipements de sauvetage maritimes: Date'
    ]
    
    disciplinary_details_columns = [
        'Date', 'Emetteur', 'Violateur', 'Fonction', 'MAT', 'Zone d\'activité',
        'Organisme', 'Description de l\'infraction', 'WPS (Worst Potential Severity)',
        'Catégorie', 'Observations Type (Positive=P/ Negative=N)', 'Risque associé',
        'Evidence Reference', 'Actions', 'Status (Ouvert/Fermé/En cours)', 'Remarques',
        'Nombre d\'avertissements'
    ]
    accidents_details_columns = [
        'N°', 'MAT', 'CIN', 'Nom', 'Prénom', 'Fonction', 'Affectation', 'date de l\'accident',
    'Nature de lésion', 'Nombre de jours d\'arret',
    'Nombre de jours de prolongation 1', 'Date d\'achèvement du certificat de prolongation',
    'Nombre de jours de prolongation 2', 'Date d\'achèvement du certificat de prolongation.1',
    'Nombre de jours prolongation 3', 'Date d\'achèvement du certificat de prolongation.2',
    'Nombre de jours prolongation 4', 'Date d\'achèvement du certificat de prolongation.3',
    'Nombre de jours prolongation 5', 'Date d\'achèvement du certificat de prolongation.4',
    'Nombre de jours prolongation 6', 'Date d\'achèvement du certificat de prolongation.5',
    'Nombre de jours prolongation 7', 'Date d\'achèvement du certificat de prolongation.6',
    'Nombre de jours prolongation 8', 'Date d\'achèvement du certificat de prolongation.7',
    'Nombre de jours prolongation 9', 'Date d\'achèvement du certificat de prolongation.8',
    'Nombre de jours prolongation 10', 'Date d\'achèvement du certificat de prolongation.9',
    'Nombre de jours prolongation 11', 'Date d\'achèvement du certificat de prolongation.10',
    'Date de reprise de travail', 'Certificat de guérison', '% d\'incapacité', 'Observations'
]
    HABILITATION_COLUMNS = [

        'MAT', 'CIN', 'Nom', 'Prénom', 'Fonction', 'Type d\'habilitation', 'Motif d\'habilitation', 'Organisme',
    'Date date de délivrance 1', 'Durée de validité 1', 'Date d\'expiration 1',
    'Date date de délivrance 2', 'Durée de validité 2', 'Date d\'expiration 2',
    'Date date de délivrance 3', 'Durée de validité 3', 'Date d\'expiration 3',
    'Observations'
]

    DISCIPLINE_COLUMNS = [
    'MAT', 'CIN', 'Emetteur', 'Violateur', 'Fonction', 'Date', 'Organisme', 'Motif de sanction 1', 'Type de sanction 1', 'Motif de sanction 2', 'Type de sanction 2', 'Motif de sanction 3', 'Type de sanction 3', 'Observations'
]
    VISITE_MEDICALE_COLUMNS = [
    'MAT', 'NOM PRENOM', 'FONCTION', 'CIN', 'CNSS', 'DATE DE NAISSANCE', 'DATE D\'EMBAUCHE',
    'Certificat d\'aptitude physique d\'embauche', 'Observations', 'DATE DERNIÈRE VISITE',
    'Date Viste programmée', 'Observations', 'Date de visite médicale 2', 'Observations', 'Observations générales'
]
    employee_info = {}
    epi_details = {}
    sens_details = {}
    formation_details = {}
    disciplinary_details = []
    accident_details = []
    habilitation_details = []
    discipline_details = []
    visite_medicale_details = []
    mat_str = str(mat)

    for key, df in dataframes.items():
        if 'MAT' in df.columns:
            if mat_str in df['MAT'].astype(str).values:
                emp_data = df[df['MAT'].astype(str) == mat_str].iloc[0]
                for col in columns_to_display:
                    if col in emp_data:
                        employee_info[col] = emp_data.get(col)
                
                # Détails des EPI
                for col in epi_details_columns:
                    if col in emp_data and pd.notna(emp_data.get(col)):
                        if ':' in col:
                            epi_type = col.split(':')[0]
                            if epi_type not in epi_details:
                                epi_details[epi_type] = {}
                            epi_details[epi_type][col.split(': ')[1]] = emp_data.get(col)
                
                # Détails des sensibilisations
                for col in sens_details_columns:
                    if col in emp_data and pd.notna(emp_data.get(col)):
                        if ':' in col:
                            sens_type = col.split(':')[0]
                            if sens_type not in sens_details:
                                sens_details[sens_type] = {}
                            sens_details[sens_type][col.split(': ')[1]] = emp_data.get(col)
                
                # Détails des formations
                for col in formation_details_columns:
                    if col in emp_data and pd.notna(emp_data.get(col)):
                        if ':' in col:
                            formation_type = col.split(':')[0]
                            if formation_type not in formation_details:
                                formation_details[formation_type] = {}
                            formation_details[formation_type][col.split(': ')[1]] = emp_data.get(col)

                # Détails disciplinaires
            # Détails disciplinaires
                if 'disciplinary' in dataframes:
                    disciplinary_df = dataframes['disciplinary']
                    if mat_str in disciplinary_df['MAT'].astype(str).values:
                        disciplinary_details = disciplinary_df[disciplinary_df['MAT'] == mat_str].to_dict(orient='records')


                 # Détails des accidents
        # Détails des accidents
            # Détails des accidents
                # Détails des accidents
                if key == 'accident':
                    accident_df = df[df['MAT'] == mat]
                    if not accident_df.empty:
                        for _, row in accident_df.iterrows():
                            accident_entry = {}
            # Récupérer les champs pertinents
                            for col in accidents_details_columns:
                                 if col in row:
                                        accident_entry[col] = row.get(col, '') if pd.notna(row.get(col, '')) else ''
                        # Calculer le nombre total de jours d'arrêt
                            def extract_days(days_str):
                
                                try:
                                    return int(days_str.split()[0])
                                except (ValueError, AttributeError, IndexError):
                                    return 0

                            total_jours_arret = extract_days(row['Nombre de jours d\'arret'])
                            for i in range(1, 12):  # Pour prolongation 1 à 11
                                if f'Nombre de jours de prolongation {i}' in row:
                                    total_jours_arret += extract_days(row[f'Nombre de jours de prolongation {i}'])

                            accident_entry['Total jours d\'arret'] = f"{total_jours_arret} jours"
                            accident_details.append(accident_entry)
                 # Détails des habilitations
                if key == 'habilitation':
                    habilitation_df = df[df['MAT'] == mat]
                    if not habilitation_df.empty:
                        for _, row in habilitation_df.iterrows():
                            habilitation_entry = {}
                            for col in HABILITATION_COLUMNS:
                                if col in row:
                                    habilitation_entry[col] = row.get(col, '') if pd.notna(row.get(col, '')) else ''
                            habilitation_details.append(habilitation_entry)
                
                                # Détails disciplinaires
                if 'discipline' in dataframes:
                    discipline_df = dataframes['discipline']
                    if mat_str in discipline_df['MAT'].astype(str).values:
                        discipline_details = discipline_df[discipline_df['MAT'] == mat_str].to_dict(orient='records')

                if 'visite_medicale' in dataframes:
                    visite_medicale_df = dataframes['visite_medicale']
                    if mat_str in visite_medicale_df['MAT'].astype(str).values:
                        visite_medicale_details = visite_medicale_df[visite_medicale_df['MAT'] == mat_str].to_dict(orient='records')

    return employee_info, epi_details, sens_details, formation_details, disciplinary_details, accident_details, habilitation_details, discipline_details, visite_medicale_details 

from flask import Flask, render_template, jsonify
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

@app.route('/epi_dashboard')
def epi_dashboard():
    df = pd.read_excel(EPI_FILE)
    
    # Répartition des EPI par SITE
    epi_by_site = df.groupby('SITE').size().reset_index(name='Nombre de EPIs')

    # Répartition des EPI par Fonction
    epi_by_function = df.groupby('FONCTION').size().reset_index(name='Nombre de EPIs')

    data = {
        'epi_by_site': {
            'labels': epi_by_site['SITE'].tolist(),
            'values': epi_by_site['Nombre de EPIs'].tolist()
        },
        'epi_by_function': {
            'labels': epi_by_function['FONCTION'].tolist(),
            'values': epi_by_function['Nombre de EPIs'].tolist()
        }
    }
    
    return render_template('epi_dashboard.html', data=data)


@app.route('/api/epi_data')
def epi_data():
    df = pd.read_excel(EPI_FILE)
    
    # Répartition des EPI par SITE
    epi_by_site = df.groupby('SITE').size().reset_index(name='Nombre de EPIs')

    # Répartition des EPI par Fonction
    epi_by_function = df.groupby('FONCTION').size().reset_index(name='Nombre de EPIs')

    data = {
        'epi_by_site': {
            'labels': epi_by_site['SITE'].tolist(),
            'values': epi_by_site['Nombre de EPIs'].tolist()
        },
        'epi_by_function': {
            'labels': epi_by_function['FONCTION'].tolist(),
            'values': epi_by_function['Nombre de EPIs'].tolist()
        }
    }
    
    return jsonify(data)



import pdfkit
from io import BytesIO
import qrcode
from flask import Flask, request, make_response, send_file, redirect, url_for, render_template, flash
import pdfkit
import qrcode
import io
import requests
import msal
import os

@app.route('/search_employee', methods=['GET', 'POST'])
def search_employee():
    if request.method == 'POST':
        mat = request.form['mat']
        # Remplacez get_employee_info par votre fonction réelle pour obtenir les détails
        employee_info, epi_details, sens_details, formation_details, disciplinary_details, accident_details, habilitation_details, discipline_details, visite_medicale_details = get_employee_info(mat)
        
        if employee_info:
            return render_template('employee_info.html',
                                   employee_info=employee_info,
                                   epi_details=epi_details,
                                   sens_details=sens_details,
                                   formation_details=formation_details,
                                   disciplinary_details=disciplinary_details,
                                   accident_details=accident_details,
                                   habilitation_details=habilitation_details,
                                   discipline_details=discipline_details,
                                   visite_medicale_details=visite_medicale_details)
        else:
            flash('MAT not found in any of the files.', 'danger')
            return redirect(url_for('search_employee'))
    
    return render_template('search_employee.html')

@app.route('/download_pdf/<mat>')
def download_pdf(mat):
    employee_info, epi_details, sens_details, formation_details, disciplinary_details, accident_details, habilitation_details, discipline_details, visite_medicale_details = get_employee_info(mat)
    if employee_info:
        # Générer le PDF
        html = render_template('employee_info.html', employee_info=employee_info, epi_details=epi_details, sens_details=sens_details, formation_details=formation_details, disciplinary_details=disciplinary_details, accident_details=accident_details, habilitation_details=habilitation_details, discipline_details=discipline_details, visite_medicale_details=visite_medicale_details)
        pdf = pdfkit.from_string(html, False, configuration=config)
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={mat}_employee_info.pdf'
        
        return response
    else:
        flash('MAT not found in any of the files.', 'danger')
        return redirect(url_for('search_employee'))
    
@app.route('/view_employee/<mat>')
def view_employee(mat):
    employee_info, epi_details, sens_details, formation_details, disciplinary_details, accident_details, habilitation_details, discipline_details, visite_medicale_details = get_employee_info(mat)
    return render_template('employee_info.html', employee_info=employee_info, epi_details=epi_details, sens_details=sens_details, formation_details=formation_details, disciplinary_details=disciplinary_details, accident_details=accident_details, habilitation_details=habilitation_details, discipline_details=discipline_details, visite_medicale_details=visite_medicale_details)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('name', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
