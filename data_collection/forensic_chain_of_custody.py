#!/usr/bin/env python3
"""
Forensische Chain of Custody Manager - Vollständige Dokumentation der Beweiskette
Stellt sicher, dass jeder Schritt der Evidenz-Behandlung vollständig dokumentiert wird
"""

import json
import hashlib
import datetime
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

class CustodyAction(Enum):
    COLLECTION = "collection"
    PROCESSING = "processing"
    ANALYSIS = "analysis"
    VERIFICATION = "verification"
    STORAGE = "storage"
    TRANSFER = "transfer"
    ACCESS = "access"
    ARCHIVAL = "archival"

class CustodyStatus(Enum):
    ACTIVE = "active"
    SECURED = "secured"
    COMPROMISED = "compromised"
    ARCHIVED = "archived"
    DESTROYED = "destroyed"

@dataclass
class CustodyEvent:
    """Einzelnes Ereignis in der Chain of Custody"""
    event_id: str
    evidence_id: str
    timestamp: str
    action: str
    actor: str
    location: str
    method: str
    status: str
    hash_before: Optional[str] = None
    hash_after: Optional[str] = None
    previous_event_id: Optional[str] = None
    next_event_id: Optional[str] = None
    metadata: Optional[Dict] = None
    legal_notes: Optional[str] = None
    technical_details: Optional[Dict] = None

class ForensicChainOfCustodyManager:
    """Verwaltet die vollständige forensische Chain of Custody"""
    
    def __init__(self, custody_log_path: Path):
        self.custody_log_path = custody_log_path
        self.custody_log = self.load_or_create_custody_log()
        
        # Logging für Chain of Custody
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - [CHAIN_OF_CUSTODY] - %(message)s',
            handlers=[
                logging.FileHandler(custody_log_path.parent / f"custody_management_{datetime.datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_or_create_custody_log(self) -> Dict:
        """Lädt existierende Chain of Custody oder erstellt neue"""
        if self.custody_log_path.exists():
            try:
                with open(self.custody_log_path, 'r', encoding='utf-8') as f:
                    custody_log = json.load(f)
                
                # Validiere Struktur
                if "chain_of_custody" not in custody_log:
                    custody_log["chain_of_custody"] = []
                if "metadata" not in custody_log:
                    custody_log["metadata"] = {}
                
                self.logger.info(f"Chain of Custody Log geladen: {len(custody_log['chain_of_custody'])} Ereignisse")
                return custody_log
                
            except Exception as e:
                self.logger.error(f"Fehler beim Laden der Chain of Custody: {e}")
        
        # Erstelle neue Chain of Custody
        new_log = {
            "chain_of_custody": [],
            "metadata": {
                "created": datetime.datetime.now().isoformat(),
                "version": "1.0",
                "manager": "ForensicChainOfCustodyManager",
                "last_updated": datetime.datetime.now().isoformat()
            }
        }
        self.logger.info("Neue Chain of Custody erstellt")
        return new_log
    
    def create_custody_event(self, 
                           evidence_id: str,
                           action: CustodyAction,
                           actor: str,
                           location: str,
                           method: str,
                           status: CustodyStatus,
                           file_path: Optional[Path] = None,
                           previous_event_id: Optional[str] = None,
                           metadata: Optional[Dict] = None,
                           legal_notes: Optional[str] = None) -> str:
        """Erstellt ein neues Chain of Custody Ereignis"""
        
        event_id = f"CUST_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
        timestamp = datetime.datetime.now().isoformat()
        
        # Berechne Hash wenn Datei vorhanden
        hash_before = None
        hash_after = None
        
        if file_path and file_path.exists():
            if action in [CustodyAction.PROCESSING, CustodyAction.ANALYSIS, CustodyAction.TRANSFER]:
                # Hash vor der Aktion
                hash_before = self.calculate_file_hash(file_path)
        
        # Erstelle Custody Event
        custody_event = CustodyEvent(
            event_id=event_id,
            evidence_id=evidence_id,
            timestamp=timestamp,
            action=action.value,
            actor=actor,
            location=location,
            method=method,
            status=status.value,
            hash_before=hash_before,
            hash_after=hash_after,
            previous_event_id=previous_event_id,
            metadata=metadata or {},
            legal_notes=legal_notes,
            technical_details=self.create_technical_details(file_path)
        )
        
        # Berechne Hash nach der Aktion wenn applicable
        if file_path and file_path.exists():
            if action in [CustodyAction.PROCESSING, CustodyAction.ANALYSIS, CustodyAction.TRANSFER]:
                hash_after = self.calculate_file_hash(file_path)
                custody_event.hash_after = hash_after
        
        # Füge Ereignis zur Chain hinzu
        self.add_custody_event(custody_event)
        
        self.logger.info(f"Custody Event erstellt: {event_id} - {action.value} für {evidence_id}")
        return event_id
    
    def add_custody_event(self, custody_event: CustodyEvent):
        """Fügt ein Ereignis zur Chain of Custody hinzu"""
        event_dict = asdict(custody_event)
        
        # Verknüpfte Events aktualisieren
        if custody_event.previous_event_id:
            self.update_event_reference(custody_event.previous_event_id, "next_event_id", custody_event.event_id)
        
        # Füge zur Chain hinzu
        self.custody_log["chain_of_custody"].append(event_dict)
        self.custody_log["metadata"]["last_updated"] = datetime.datetime.now().isoformat()
        
        # Speichere sofort
        self.save_custody_log()
    
    def update_event_reference(self, event_id: str, reference_field: str, reference_value: str):
        """Aktualisiert eine Referenz in einem existierenden Ereignis"""
        for event in self.custody_log["chain_of_custody"]:
            if event["event_id"] == event_id:
                event[reference_field] = reference_value
                break
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Berechnet SHA-256 Hash einer Datei"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            self.logger.error(f"Fehler bei Hash-Berechnung für {file_path}: {e}")
            return None
    
    def create_technical_details(self, file_path: Optional[Path]) -> Dict:
        """Erstellt technische Details für das Ereignis"""
        details = {
            "platform": sys.platform,
            "python_version": sys.version,
            "working_directory": os.getcwd(),
            "process_id": os.getpid()
        }
        
        if file_path and file_path.exists():
            stat = file_path.stat()
            details.update({
                "file_size": stat.st_size,
                "file_permissions": oct(stat.st_mode)[-3:],
                "creation_time": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modification_time": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "access_time": datetime.datetime.fromtimestamp(stat.st_atime).isoformat()
            })
        
        return details
    
    def get_evidence_chain(self, evidence_id: str) -> List[Dict]:
        """Holt die vollständige Chain of Custody für eine Evidenz"""
        chain = []
        
        for event in self.custody_log["chain_of_custody"]:
            if event["evidence_id"] == evidence_id:
                chain.append(event)
        
        # Sortiere nach Zeitstempel
        chain.sort(key=lambda x: x["timestamp"])
        
        return chain
    
    def validate_chain_integrity(self, evidence_id: str) -> Dict:
        """Validiert die Integrität der Chain of Custody für eine Evidenz"""
        chain = self.get_evidence_chain(evidence_id)
        
        validation_result = {
            "evidence_id": evidence_id,
            "validation_timestamp": datetime.datetime.now().isoformat(),
            "is_valid": True,
            "total_events": len(chain),
            "integrity_issues": [],
            "missing_links": [],
            "hash_mismatches": [],
            "timeline_gaps": []
        }
        
        if not chain:
            validation_result["is_valid"] = False
            validation_result["integrity_issues"].append("No chain of custody events found")
            return validation_result
        
        # Prüfe auf Lücken in der Kette
        for i, event in enumerate(chain):
            if i > 0:
                prev_event = chain[i-1]
                
                # Prüfe Verknüpfungen
                if event["previous_event_id"] != prev_event["event_id"]:
                    validation_result["missing_links"].append(f"Link break between {prev_event['event_id']} and {event['event_id']}")
                    validation_result["is_valid"] = False
                
                # Prüfe Zeitstempel-Logik
                try:
                    current_time = datetime.datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                    prev_time = datetime.datetime.fromisoformat(prev_event["timestamp"].replace('Z', '+00:00'))
                    
                    if current_time < prev_time:
                        validation_result["timeline_gaps"].append(f"Timeline inconsistency: {event['event_id']}")
                        validation_result["is_valid"] = False
                        
                except ValueError:
                    validation_result["integrity_issues"].append(f"Invalid timestamp format in {event['event_id']}")
                    validation_result["is_valid"] = False
        
        # Prüfe Hash-Konsistenz
        for event in chain:
            if event.get("hash_before") and event.get("hash_after"):
                if event["hash_before"] != event["hash_after"]:
                    validation_result["hash_mismatches"].append(f"Hash mismatch in {event['event_id']}")
                    validation_result["is_valid"] = False
        
        return validation_result
    
    def generate_custody_report(self, evidence_id: Optional[str] = None) -> Dict:
        """Generiert einen vollständigen Chain of Custody Bericht"""
        report_timestamp = datetime.datetime.now().isoformat()
        
        if evidence_id:
            # Bericht für spezifische Evidenz
            chain = self.get_evidence_chain(evidence_id)
            validation = self.validate_chain_integrity(evidence_id)
            
            report = {
                "report_type": "evidence_specific",
                "report_timestamp": report_timestamp,
                "evidence_id": evidence_id,
                "chain_of_custody": chain,
                "chain_validation": validation,
                "summary": {
                    "total_events": len(chain),
                    "is_valid": validation["is_valid"],
                    "first_event": chain[0]["timestamp"] if chain else None,
                    "last_event": chain[-1]["timestamp"] if chain else None
                }
            }
        else:
            # Vollständiger Bericht für alle Evidenzen
            all_evidence_ids = set(event["evidence_id"] for event in self.custody_log["chain_of_custody"])
            
            evidence_reports = {}
            for ev_id in all_evidence_ids:
                chain = self.get_evidence_chain(ev_id)
                validation = self.validate_chain_integrity(ev_id)
                
                evidence_reports[ev_id] = {
                    "total_events": len(chain),
                    "is_valid": validation["is_valid"],
                    "issues": len(validation["integrity_issues"]),
                    "first_event": chain[0]["timestamp"] if chain else None,
                    "last_event": chain[-1]["timestamp"] if chain else None
                }
            
            report = {
                "report_type": "full_chain",
                "report_timestamp": report_timestamp,
                "total_evidence_items": len(all_evidence_ids),
                "total_events": len(self.custody_log["chain_of_custody"]),
                "evidence_summaries": evidence_reports,
                "chain_metadata": self.custody_log["metadata"]
            }
        
        return report
    
    def save_custody_log(self):
        """Speichert die Chain of Custody Log-Datei"""
        try:
            with open(self.custody_log_path, 'w', encoding='utf-8') as f:
                json.dump(self.custody_log, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern der Chain of Custody: {e}")
    
    def create_backup(self, backup_dir: Path):
        """Erstellt ein Backup der Chain of Custody"""
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True)
        
        backup_filename = f"chain_of_custody_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = backup_dir / backup_filename
        
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self.custody_log, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Chain of Custody Backup erstellt: {backup_filename}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Fehler beim Erstellen des Backups: {e}")
            return None

def main():
    """Hauptfunktion für Chain of Custody Management"""
    base_dir = Path(__file__).parent
    log_dir = base_dir / "logs"
    custody_log_path = log_dir / "chain_of_custody.json"
    
    print("=== Forensische Chain of Custody Manager ===")
    print("Vollständige Dokumentation der Beweiskette")
    
    manager = ForensicChainOfCustodyManager(custody_log_path)
    
    try:
        # Generiere Bericht
        print("Generiere Chain of Custody Bericht...")
        report = manager.generate_custody_report()
        
        print(f"\n=== CHAIN OF CUSTODY BERICHTE ===")
        if report["report_type"] == "full_chain":
            print(f"Gesamt-Evidenz-Items: {report['total_evidence_items']}")
            print(f"Gesamt-Ereignisse: {report['total_events']}")
            
            print(f"\nEvidenz-Übersicht:")
            for ev_id, summary in report["evidence_summaries"].items():
                status = "✅ VALID" if summary["is_valid"] else "❌ INVALID"
                print(f"  {ev_id}: {summary['total_events']} Events - {status}")
        
        # Speichere Bericht
        report_filename = f"custody_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = log_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nBericht gespeichert: {report_filename}")
        
    except Exception as e:
        print(f"Fehler bei Chain of Custody Management: {e}")

if __name__ == "__main__":
    main()
