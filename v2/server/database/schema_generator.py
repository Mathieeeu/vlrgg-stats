"""
Générateur automatique de schéma SQL à partir des modèles Python
(généré avec ia (claude))
"""

import inspect
from typing import get_type_hints, get_origin, get_args, Optional, Dict, Any, List, Union
from dataclasses import fields, is_dataclass
from datetime import date as date_type, datetime
import os

from .models import (
    MODEL_TO_TABLE, AUTO_INCREMENT_MODELS, USER_DEFINED_KEY_MODELS, 
    FOREIGN_KEY_FIELDS, Event, Team, Player, Match, Game, MatchTeam, 
    GameScore, EconomyStats, RoundHistory, PlayerStats
)


class SchemaGenerator:
    """Générateur de schéma SQL à partir des modèles dataclass"""
    
    # Mapping des types Python vers les types SQL SQLite
    TYPE_MAPPING = {
        int: 'INTEGER',
        str: 'TEXT',
        float: 'REAL',
        bool: 'BOOLEAN',
        date_type: 'DATE',
        datetime: 'TIMESTAMP',
    }
    
    def __init__(self):
        self.models = [Event, Team, Player, Match, Game, MatchTeam, 
                      GameScore, EconomyStats, RoundHistory, PlayerStats]
    
    def get_sql_type(self, field_type: Any) -> str:
        """Convertir un type Python en type SQL SQLite"""
        # Gérer les types Optional (Union[Type, None])
        origin = get_origin(field_type)
        
        if origin is Union:
            # C'est un Optional[Type] ou Union[Type, None]
            args = get_args(field_type)
            if len(args) == 2 and type(None) in args:
                # C'est Optional[Type], extraire le type réel
                non_none_type = args[0] if args[1] is type(None) else args[1]
                return self.TYPE_MAPPING.get(non_none_type, 'TEXT')
        
        # Type direct
        return self.TYPE_MAPPING.get(field_type, 'TEXT')
    
    def get_primary_key_definition(self, model_class) -> tuple:
        """Retourner la définition de clé primaire pour un modèle"""
        table_name = MODEL_TO_TABLE[model_class]
        
        # Identifier la clé primaire depuis les champs du modèle
        model_fields = fields(model_class)
        primary_key_field = None
        
        # Conventions de nommage des clés primaires
        for field in model_fields:
            if field.name in ['id', f'{table_name[:-1]}_id', 'match_id', 'game_id']:
                primary_key_field = field
                break
        
        if not primary_key_field:
            raise ValueError(f"Impossible de trouver la clé primaire pour {model_class.__name__}")
        
        # Déterminer si c'est auto-increment
        is_auto_increment = model_class in AUTO_INCREMENT_MODELS
        
        if is_auto_increment:
            return (primary_key_field.name, "INTEGER PRIMARY KEY AUTOINCREMENT")
        else:
            sql_type = self.get_sql_type(primary_key_field.type)
            return (primary_key_field.name, f"{sql_type} PRIMARY KEY")
    
    def get_foreign_key_constraints(self, table_name: str) -> List[str]:
        """Générer les contraintes de clés étrangères pour une table"""
        constraints = []
        foreign_keys = FOREIGN_KEY_FIELDS.get(table_name, {})
        
        for fk_field, (ref_table, ref_column) in foreign_keys.items():
            constraint = f"FOREIGN KEY ({fk_field}) REFERENCES {ref_table}({ref_column})"
            constraints.append(constraint)
        
        return constraints
    
    def generate_table_sql(self, model_class) -> str:
        """Générer le SQL CREATE TABLE pour un modèle"""
        table_name = MODEL_TO_TABLE[model_class]
        model_fields = fields(model_class)
        
        # Obtenir la clé primaire
        pk_field_name, pk_definition = self.get_primary_key_definition(model_class)
        
        # Construire les colonnes
        columns = []
        
        for field in model_fields:
            if field.name == pk_field_name:
                # La clé primaire est déjà définie
                columns.append(f"    {field.name} {pk_definition}")
            else:
                sql_type = self.get_sql_type(field.type)
                
                # Déterminer si le champ peut être NULL
                is_optional = get_origin(field.type) is Union and type(None) in get_args(field.type)
                null_constraint = "" if is_optional else " NOT NULL"
                
                # Valeur par défaut
                default_value = ""
                if field.default is not None and field.default != field.default_factory:
                    if isinstance(field.default, str):
                        default_value = f" DEFAULT '{field.default}'"
                    else:
                        default_value = f" DEFAULT {field.default}"
                
                column_def = f"    {field.name} {sql_type}{null_constraint}{default_value}"
                columns.append(column_def)
        
        # Ajouter les contraintes de clés étrangères
        fk_constraints = self.get_foreign_key_constraints(table_name)
        for constraint in fk_constraints:
            columns.append(f"    {constraint}")
        
        # Construire le SQL final
        columns_sql = ",\n".join(columns)
        
        sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
{columns_sql}
);"""
        
        return sql
    
    def generate_full_schema(self) -> str:
        """Générer le schéma complet pour toutes les tables"""
        schema_parts = []
        
        # En-tête
        schema_parts.append("-- Schéma généré automatiquement à partir des modèles Python")
        schema_parts.append("-- Ne pas modifier manuellement - utiliser schema_generator.py")
        schema_parts.append("")
        
        # Activer les clés étrangères
        schema_parts.append("PRAGMA foreign_keys = ON;")
        schema_parts.append("")
        
        # Générer les tables dans l'ordre des dépendances
        # Tables sans dépendances d'abord
        independent_tables = [Event, Team, Player]
        dependent_tables = [Match, Game, MatchTeam, GameScore, EconomyStats, RoundHistory, PlayerStats]
        
        for model_class in independent_tables + dependent_tables:
            schema_parts.append(self.generate_table_sql(model_class))
            schema_parts.append("")
        
        return "\n".join(schema_parts)
    
    def save_schema_to_file(self, output_path: str = None) -> str:
        """Sauvegarder le schéma dans un fichier SQL"""
        if output_path is None:
            # Chemin par défaut
            output_path = os.path.join(
                os.path.dirname(__file__), '..', 'db', 'schema.sql'
            )
        
        # Créer le répertoire si nécessaire
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        schema_sql = self.generate_full_schema()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(schema_sql)
        
        return output_path


def generate_schema():
    """Fonction utilitaire pour générer le schéma"""
    generator = SchemaGenerator()
    output_path = generator.save_schema_to_file()
    print(f"Schéma généré et sauvegardé dans: {output_path}")
    return output_path


if __name__ == "__main__":
    # Génération du schéma quand le script est exécuté directement
    generate_schema()