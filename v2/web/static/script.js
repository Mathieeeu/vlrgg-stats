
// variables globales
let tablesData = [];

// Requêtes predefinies
const predefinedQueries = [
    {
        title: "Derniers événements",
        description: "Affiche les événements collectés les plus récents",
        query: 
`SELECT 
    title, 
    start_date, 
    end_date, 
    region, 
    location, 
    status, 
    url
FROM events 
ORDER BY start_date DESC;
`
    },
    {
        title: "Matches joués par équipe",
        description: "Nombre total de matchs joués par équipe",
        query: 
`SELECT 
    t.name, 
    t.region, 
    COUNT(mt.match_id) as matches_played
FROM teams t 
LEFT JOIN match_teams mt ON t.id = mt.team_id 
GROUP BY t.id, t.name, t.region 
ORDER BY matches_played DESC;
`
    },
    {
        title: "Meilleurs ACS",
        description: "Top 20 des joueurs avec le meilleur ACS moyen (minimum 5 games)",
        query: 
`SELECT 
    p.name, 
    ROUND(AVG(ps.acs_both), 1) as avg_acs, 
    COUNT(*) as games, 
    COUNT(DISTINCT g.match_id) as matches 
FROM players p 
JOIN player_stats ps ON p.id = ps.player_id 
JOIN games g ON ps.game_id = g.game_id 
WHERE ps.acs_both IS NOT NULL 
GROUP BY p.id, p.name HAVING games >= 5 
ORDER BY avg_acs DESC LIMIT 20;
`
    },
    {
        title: "Nombre de matchs par événement",
        description: "Événements classés par nombre total de parties et de matchs joués",
        query: 
`SELECT 
    e.title, 
    COUNT(DISTINCT(m.match_id)) as total_matches,
    COUNT(g.game_id) as total_games
FROM events e 
LEFT JOIN matches m ON e.id = m.event_id
LEFT JOIN games g ON g.match_id = m.match_id
GROUP BY e.id, e.title 
ORDER BY total_matches DESC, total_games DESC;
`
    },
    {
        title: "Statistiques d'un joueur",
        description: "Historique des performances (ici les éliminations) d'un joueur",
        query: 
`SELECT 
    players.name,
    player_stats.k_both,
    games.map,
    matches.date,
    events.title,
    matches.series 
FROM players 
JOIN player_stats on player_stats.player_id = players.id 
JOIN games on player_stats.game_id = games.game_id 
JOIN matches on games.match_id = matches.match_id 
JOIN events on matches.event_id = events.id 
JOIN teams on teams.id = player_stats.team_id 
WHERE players.name = "westside" 
ORDER BY date desc;
`
    },
    {
        title: "Nombre de parties par carte",
        description: "Les cartes les plus jouées en VCT, tout simplement.",
        query:
`SELECT 
    map, 
    COUNT(*) as play_count 
FROM games 
GROUP BY map 
ORDER BY play_count DESC;
`
    },
    {
        title: "Winrate par région",
        description: "Winrate des équipes par région aux événements internationaux",
        query: 
`SELECT 
    e.id AS event_id,
    e.title AS event_name,
    e.start_date,
    t.region AS team_region,
    COUNT(CASE WHEN mt.is_winner = 1 THEN 1 END) AS wins,
    COUNT(*) AS total_matches,
    ROUND(1.0 * COUNT(CASE WHEN mt.is_winner = 1 THEN 1 END) / COUNT(*), 4) AS winrate
FROM teams t
JOIN match_teams mt ON t.id = mt.team_id
JOIN matches m ON mt.match_id = m.match_id
JOIN events e ON m.event_id = e.id
WHERE e.region = 'inter'
    AND t.region IS NOT NULL
    AND m.date IS NOT NULL
    AND m.date >= date('now', '-3 years')
GROUP BY e.id, e.title, e.start_date, t.region
ORDER BY e.start_date DESC, e.title, t.region
LIMIT 200;
`
    },
    {
	title: "Statistiques de cartes pour une équipe",
	description: "Nombre de parties, nombre de rounds gagnés moyen et winrate par carte pour une équipe donnée (ici Fnatic)",
	query:
`SELECT 
    games.map, 
    COUNT(*) AS played,
    ROUND(AVG(game_scores.score), 1) AS avg_score,
    ROUND(
        100.0 * SUM(CASE WHEN games.win = teams.id THEN 1 ELSE 0 END) / COUNT(*),
        1
    ) AS winrate
FROM games 
JOIN game_scores ON game_scores.game_id = games.game_id
JOIN teams ON teams.id = game_scores.team_id
WHERE teams.short_name = "FNC"
GROUP BY games.map 
ORDER BY winrate DESC;
`
    }
];

// init la page
document.addEventListener('DOMContentLoaded', function() {
    loadTables();
    displayPredefinedQueries();
});

function displayPredefinedQueries() {
    const container = document.getElementById('queries-grid');
    container.innerHTML = '';
    
    predefinedQueries.forEach((queryData, index) => {
        const card = createQueryCard(queryData, index);
        container.appendChild(card);
    });
}

// fct pour faire une carte de requete predefinie
function createQueryCard(queryData, index) {
    const card = document.createElement('div');
    card.className = 'query-card';
    card.onclick = () => setQueryFromCard(queryData.query);
    
    const title = document.createElement('div');
    title.className = 'query-card-title';
    title.textContent = queryData.title;
    
    const description = document.createElement('div');
    description.className = 'query-card-description';
    description.textContent = queryData.description;
    
    const preview = document.createElement('div');
    preview.className = 'query-card-preview';
    preview.textContent = queryData.query;
    
    card.appendChild(title);
    card.appendChild(description);
    card.appendChild(preview);
    
    return card;
}

function setQueryFromCard(query) {
    const textarea = document.getElementById('queryTextarea');
    textarea.value = query;
    textarea.focus();
    
    textarea.scrollIntoView({ behavior: 'smooth', block: 'center' }); // petit scroll vers la zone de requete
}

async function loadTables() {
    try {
        const response = await fetch('/api/tables');
        tablesData = await response.json();
        displayTables();
    } catch (error) {
        console.error('Erreur lors du chargement des tables:', error);
        document.getElementById('tables-container').innerHTML = 
            '<div class="loading-tables">Erreur lors du chargement des tables</div>';
    }
}

function displayTables() {
    const container = document.getElementById('tables-container');
    
    if (tablesData.length === 0) {
        container.innerHTML = '<div class="loading-tables">Aucune table trouvée</div>';
        return;
    }
    
    container.innerHTML = '';
    
    const filteredTables = tablesData.filter(table => table.name !== 'sqlite_sequence' && table.name !== 'utils'); // on enleve les tables sqlite_sequence et utils
    
    filteredTables.forEach(table => {
        const tableCard = createTableCard(table);
        container.appendChild(tableCard);
    });
}

function createTableCard(table) {
    const card = document.createElement('div');
    card.className = 'table-card';
    card.setAttribute('data-table', table.name);
    
    const header = document.createElement('div');
    header.className = 'table-header';
    header.onclick = () => toggleTableCard(card);
    
    const nameElement = document.createElement('h4');
    nameElement.className = 'table-name';
    nameElement.textContent = table.name;
    
    const countElement = document.createElement('span');
    countElement.className = 'table-count';
    countElement.textContent = `${table.row_count} lignes`;
    
    const expandIcon = document.createElement('span');
    expandIcon.className = 'expand-icon';
    expandIcon.textContent = '▼';
    
    header.appendChild(nameElement);
    header.appendChild(countElement);
    header.appendChild(expandIcon);
    
    const columnsList = document.createElement('div');
    columnsList.className = 'columns-list';
    
    table.columns.forEach(column => {
        const columnItem = document.createElement('div');
        columnItem.className = 'column-item';
        columnItem.onclick = () => addColumnToQuery(table.name, column.name);
        
        const columnName = document.createElement('span');
        columnName.className = 'column-name';
        columnName.textContent = column.name;
        
        const columnType = document.createElement('span');
        columnType.className = `column-type ${column.primary_key ? 'primary-key' : ''}`;
        columnType.textContent = column.primary_key ? 'PK' : column.type;
        
        columnItem.appendChild(columnName);
        columnItem.appendChild(columnType);
        columnsList.appendChild(columnItem);
    });
    
    card.appendChild(header);
    card.appendChild(columnsList);
    
    return card;
}

function toggleTableCard(card) { //cartes de la sidebar
    card.classList.toggle('expanded');
}

// ajouter une variable à la requête en cours
function addColumnToQuery(tableName, columnName) {
    const textarea = document.getElementById('queryTextarea');
    const cursorPos = textarea.selectionStart;
    const textBefore = textarea.value.substring(0, cursorPos);
    const textAfter = textarea.value.substring(cursorPos);
    
    const insertion = `${tableName}.${columnName}`;
    textarea.value = textBefore + insertion + textAfter;
    
    const newPos = cursorPos + insertion.length;
    textarea.setSelectionRange(newPos, newPos);
    textarea.focus();
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

function executeQuery() {
    const query = document.getElementById('queryTextarea').value.trim();
    
    if (!query) {
        alert('Veuillez entrer une requête');
        return;
    }

    // Masquer les sections des requetes d'avant 
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    document.getElementById('loading').style.display = 'block';

    fetch('/api/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('loading').style.display = 'none';
        
        if (data.error) {
            showError(data.error);
        } else {
            showResults(data);
        }
    })
    .catch(error => {
        document.getElementById('loading').style.display = 'none';
        showError('Erreur de connexion: ' + error.message);
    });
}

function showResults(data) {
    document.getElementById('error').style.display = 'none';
    document.getElementById('results').style.display = 'block';

    // Stocker les données pour le téléchargement CSV
    currentResultData = data;

    const resultsInfo = document.getElementById('results-info');
    
    // Créer le contenu avec le message et le bouton (si il y a des résultats)
    if (data.data.length > 0) {
        resultsInfo.innerHTML = `
            <span>${data.count} résultat(s) trouvé(s)</span>
            <button class="download-csv-btn" onclick="downloadCSV()" title="Télécharger en CSV">
                Télécharger CSV
            </button>
        `;
    } else {
        resultsInfo.textContent = `${data.count} résultat(s) trouvé(s)`;
    }

    const header = document.getElementById('results-header');
    const body = document.getElementById('results-body');

    header.innerHTML = '';
    body.innerHTML = '';

    if (data.data.length === 0) {
        body.innerHTML = '<tr><td colspan="100%">Aucun résultat</td></tr>';
        return;
    }

    const headerRow = document.createElement('tr');
    data.columns.forEach(column => {
        const th = document.createElement('th');
        th.textContent = column;
        headerRow.appendChild(th);
    });
    header.appendChild(headerRow);

    data.data.forEach(row => {
        const tr = document.createElement('tr');
        data.columns.forEach(column => {
            const td = document.createElement('td');
            const value = row[column];
            td.textContent = value !== null && value !== undefined ? value : '';
            tr.appendChild(td);
        });
        body.appendChild(tr);
    });
}

function showError(message) {
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'block';
    document.getElementById('error-message').textContent = message;
}

// variable pour stocker les dernières données de résultat
let currentResultData = null;

function downloadCSV() {
    if (!currentResultData || !currentResultData.data || currentResultData.data.length === 0) {
        alert('Aucune donnée à télécharger');
        return;
    }

    // Créer le contenu CSV
    let csvContent = '';
    
    // Ajouter l'en-tête (noms des colonnes)
    csvContent += currentResultData.columns.join(',') + '\n';
    
    // Ajouter les données
    currentResultData.data.forEach(row => {
        const rowData = currentResultData.columns.map(column => {
            let value = row[column];
            
            // Gérer les valeurs nulles/undefined
            if (value === null || value === undefined) {
                value = '';
            }
            
            // Échapper les guillemets et encapsuler les valeurs contenant des virgules ou des guillemets
            value = String(value);
            if (value.includes(',') || value.includes('"') || value.includes('\n')) {
                value = '"' + value.replace(/"/g, '""') + '"';
            }
            
            return value;
        });
        csvContent += rowData.join(',') + '\n';
    });

    // Créer le blob et déclencher le téléchargement
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `resultats_requete_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
}

function clearQuery() {
    document.getElementById('queryTextarea').value = '';
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';
}

// ctrl+entrée pour executer la requete ;)
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') {
        executeQuery();
    }
});
