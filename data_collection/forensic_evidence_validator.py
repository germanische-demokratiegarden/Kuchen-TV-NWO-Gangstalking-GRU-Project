#!/usr/bin/env python3
"""
Forensischer Evidenz-Validator - Wissenschaftliche Gütesicherung für digitale Beweise
Stellt sicher, dass alle gesammelten Daten forensischen Standards entsprechen
"""

import json
import hashlib
import datetime
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
from enum import Enum

class EvidenceLevel(Enum):
    STANDARD = "standard"
    VERIFIED = "verified"
    CRITICAL = "critical"
    COMPROMISED = "compromised"

class VerificationStatus(Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"

@dataclass
class ForensicStandards:
    """Definiert forensische Standards für digitale Evidenz"""
    hash_algorithm: str = "SHA-256"
    timestamp_format: str = "ISO8601"
    encoding: str = "UTF-8"
    chain_of_custody_required: bool = True
    integrity_verification: bool = True
    legal_annotation_required: bool = True
    technical_analysis_required: bool = True
    retention_period_years: int = 10

class ForensicEvidenceValidator:
    """Validiert digitale Evidenz nach forensisch-wissenschaftlichen Standards"""
    
    def __init__(self, evidence_dir: Path, log_dir: Path):
        self.evidence_dir = evidence_dir
        self.log_dir = log_dir
        self.standards = ForensicStandards()
        
        # Logging für forensische Validierung
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - [FORENSIC_VALIDATOR] - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / f"forensic_validation_{datetime.datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Validierungsstatistiken
        self.validation_stats = {
            "total_evidence_files": 0,
            "valid_evidence": 0,
            "invalid_evidence": 0,
            "compromised_evidence": 0,
            "validation_errors": []
        }
    
    def validate_all_evidence(self) -> Dict:
        """Validiert alle Evidenz-Dateien im Verzeichnis"""
        self.logger.info("Starte umfassende forensische Validierung")
        
        evidence_files = list(self.evidence_dir.glob("*.json"))
        self.validation_stats["total_evidence_files"] = len(evidence_files)
        
        validation_results = {
            "validation_timestamp": datetime.datetime.now().isoformat(),
            "validator_version": "1.0",
            "standards_applied": self.standards.__dict__,
            "evidence_validation": [],
            "summary": {},
            "recommendations": []
        }
        
        for evidence_file in evidence_files:
            try:
                result = self.validate_single_evidence_file(evidence_file)
                validation_results["evidence_validation"].append(result)
                
                if result["is_valid"]:
                    self.validation_stats["valid_evidence"] += 1
                else:
                    self.validation_stats["invalid_evidence"] += 1
                    
                if result["evidence_level"] == EvidenceLevel.COMPROMISED.value:
                    self.validation_stats["compromised_evidence"] += 1
                    
            except Exception as e:
                error_msg = f"Fehler bei Validierung von {evidence_file.name}: {e}"
                self.logger.error(error_msg)
                self.validation_stats["validation_errors"].append(error_msg)
        
        # Erstelle Zusammenfassung
        validation_results["summary"] = self.create_validation_summary()
        validation_results["recommendations"] = self.generate_recommendations()
        
        # Speichere Validierungsbericht
        self.save_validation_report(validation_results)
        
        return validation_results
    
    def validate_single_evidence_file(self, evidence_file: Path) -> Dict:
        """Validiert eine einzelne Evidenz-Datei"""
        self.logger.info(f"Validiere Evidenz-Datei: {evidence_file.name}")
        
        validation_result = {
            "file_name": evidence_file.name,
            "file_path": str(evidence_file),
            "validation_timestamp": datetime.datetime.now().isoformat(),
            "is_valid": False,
            "evidence_level": EvidenceLevel.STANDARD.value,
            "verification_status": VerificationStatus.PENDING.value,
            "validation_checks": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            with open(evidence_file, 'r', encoding='utf-8') as f:
                evidence_data = json.load(f)
            
            # Führe alle forensischen Validierungen durch
            validation_result["validation_checks"]["structure"] = self.validate_evidence_structure(evidence_data)
            validation_result["validation_checks"]["integrity"] = self.validate_data_integrity(evidence_data, evidence_file)
            validation_result["validation_checks"]["metadata"] = self.validate_forensic_metadata(evidence_data)
            validation_result["validation_checks"]["chain_of_custody"] = self.validate_chain_of_custody(evidence_data)
            validation_result["validation_checks"]["legal_compliance"] = self.validate_legal_compliance(evidence_data)
            validation_result["validation_checks"]["technical_analysis"] = self.validate_technical_analysis(evidence_data)
            
            # Bestimme Gesamtvalidität
            all_checks_passed = all(
                check["passed"] for check in validation_result["validation_checks"].values()
            )
            validation_result["is_valid"] = all_checks_passed
            
            # Bestimme Evidenz-Level
            validation_result["evidence_level"] = self.determine_evidence_level(evidence_data, validation_result)
            validation_result["verification_status"] = self.determine_verification_status(validation_result)
            
        except Exception as e:
            validation_result["errors"].append(f"Dateilesung/-parsung Fehler: {e}")
            validation_result["evidence_level"] = EvidenceLevel.COMPROMISED.value
        
        return validation_result
    
    def validate_evidence_structure(self, evidence_data: Dict) -> Dict:
        """Validiert die grundlegende Evidenz-Struktur"""
        required_fields = [
            "evidence_id", "timestamp", "category", "source", 
            "data", "forensic_metadata", "verification_chain"
        ]
        
        result = {
            "passed": True,
            "details": {},
            "missing_fields": [],
            "unexpected_fields": []
        }
        
        # Prüfe erforderliche Felder
        for field in required_fields:
            if field not in evidence_data:
                result["passed"] = False
                result["missing_fields"].append(field)
            else:
                result["details"][field] = "present"
        
        # Prüfe unerwartete Strukturen
        if not isinstance(evidence_data.get("data"), dict):
            result["passed"] = False
            result["unexpected_fields"].append("data should be dict")
        
        return result
    
    def validate_data_integrity(self, evidence_data: Dict, evidence_file: Path) -> Dict:
        """Validiert Datenintegrität mit Hash-Verifizierung"""
        result = {
            "passed": True,
            "details": {},
            "hash_verification": {},
            "file_consistency": {}
        }
        
        try:
            # Prüfe Hash in Metadaten
            metadata = evidence_data.get("forensic_metadata", {})
            stored_hash = metadata.get("data_integrity", {}).get("hash")
            
            if not stored_hash:
                result["passed"] = False
                result["hash_verification"]["error"] = "Kein Hash in Metadaten gefunden"
                return result
            
            # Berechne aktuellen Hash
            data_string = json.dumps(evidence_data, sort_keys=True, ensure_ascii=False)
            current_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
            
            result["hash_verification"]["stored_hash"] = stored_hash
            result["hash_verification"]["calculated_hash"] = current_hash
            result["hash_verification"]["matches"] = stored_hash == current_hash
            
            if stored_hash != current_hash:
                result["passed"] = False
                result["hash_verification"]["error"] = "Hash-Übereinstimmung fehlgeschlagen - Daten manipuliert"
            
            # Prüfe Dateigröße-Konsistenz
            file_size = evidence_file.stat().st_size
            stored_size = metadata.get("data_integrity", {}).get("original_size")
            
            result["file_consistency"]["file_size"] = file_size
            result["file_consistency"]["stored_size"] = stored_size
            result["file_consistency"]["consistent"] = str(file_size) == str(stored_size)
            
        except Exception as e:
            result["passed"] = False
            result["hash_verification"]["error"] = f"Hash-Verifizierung Fehler: {e}"
        
        return result
    
    def validate_forensic_metadata(self, evidence_data: Dict) -> Dict:
        """Validiert forensische Metadaten"""
        result = {
            "passed": True,
            "details": {},
            "missing_metadata": []
        }
        
        metadata = evidence_data.get("forensic_metadata", {})
        required_metadata = [
            "collection_timestamp", "collection_method", "evidence_level",
            "verification_status", "chain_of_custody", "data_integrity", "legal_compliance"
        ]
        
        for meta_field in required_metadata:
            if meta_field not in metadata:
                result["passed"] = False
                result["missing_metadata"].append(meta_field)
            else:
                result["details"][meta_field] = "present"
        
        # Prüfe Zeitstempel-Format
        timestamp = metadata.get("collection_timestamp")
        if timestamp:
            try:
                datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                result["details"]["timestamp_format"] = "valid_iso8601"
            except ValueError:
                result["passed"] = False
                result["details"]["timestamp_format"] = "invalid_iso8601"
        
        return result
    
    def validate_chain_of_custody(self, evidence_data: Dict) -> Dict:
        """Validiert Chain of Custody"""
        result = {
            "passed": True,
            "details": {},
            "custody_breaks": []
        }
        
        custody = evidence_data.get("forensic_metadata", {}).get("chain_of_custody", {})
        
        # Prüfe erforderliche Chain of Custody Felder
        required_custody_fields = ["collector", "collection_environment", "process_id"]
        
        for field in required_custody_fields:
            if field not in custody:
                result["passed"] = False
                result["custody_breaks"].append(f"Missing custody field: {field}")
            else:
                result["details"][field] = "present"
        
        # Prüfe Verifizierungskette
        verification_chain = evidence_data.get("verification_chain", {})
        if verification_chain:
            result["details"]["verification_chain_present"] = True
            
            # Prüfe ob alle Verifizierungsschritte vorhanden sind
            required_steps = ["initial_collection", "data_integrity_check", "source_verification"]
            for step in required_steps:
                if step not in verification_chain:
                    result["custody_breaks"].append(f"Missing verification step: {step}")
                else:
                    result["details"][f"verification_{step}"] = "present"
        else:
            result["passed"] = False
            result["custody_breaks"].append("No verification chain found")
        
        return result
    
    def validate_legal_compliance(self, evidence_data: Dict) -> Dict:
        """Validiert rechtliche Compliance"""
        result = {
            "passed": True,
            "details": {},
            "compliance_issues": []
        }
        
        legal = evidence_data.get("forensic_metadata", {}).get("legal_compliance", {})
        
        # Prüfe GDPR-Compliance
        if legal.get("data_protection") != "GDPR_compliant":
            result["passed"] = False
            result["compliance_issues"].append("GDPR compliance not confirmed")
        
        # Prüfe Zugriffskontrollen
        if legal.get("access_level") != "law_enforcement_only":
            result["compliance_issues"].append("Access level not properly restricted")
        
        # Prüfe rechtliche Anmerkungen
        legal_annotation = evidence_data.get("legal_annotation", {})
        if not legal_annotation:
            result["passed"] = False
            result["compliance_issues"].append("No legal annotation provided")
        
        return result
    
    def validate_technical_analysis(self, evidence_data: Dict) -> Dict:
        """Validiert technische Analyse"""
        result = {
            "passed": True,
            "details": {},
            "technical_issues": []
        }
        
        tech_analysis = evidence_data.get("technical_analysis", {})
        
        if not tech_analysis:
            result["passed"] = False
            result["technical_issues"].append("No technical analysis provided")
            return result
        
        # Prüfe Sammlungsumgebung
        collection_env = tech_analysis.get("collection_environment", {})
        required_env_fields = ["platform", "python_version", "working_directory"]
        
        for field in required_env_fields:
            if field not in collection_env:
                result["technical_issues"].append(f"Missing environment field: {field}")
        
        # Prüfe Datencharakteristiken
        data_chars = tech_analysis.get("data_characteristics", {})
        if not data_chars.get("size_bytes"):
            result["technical_issues"].append("No data size information")
        
        return result
    
    def determine_evidence_level(self, evidence_data: Dict, validation_result: Dict) -> str:
        """Bestimmt den Evidenz-Level basierend auf Validierung"""
        if not validation_result["is_valid"]:
            return EvidenceLevel.COMPROMISED.value
        
        # Prüfe auf kritische Evidenz
        category = evidence_data.get("category", "")
        if category in ["critical", "high_priority"]:
            return EvidenceLevel.CRITICAL.value
        
        # Prüfe Verifizierungsstatus
        verification_status = evidence_data.get("forensic_metadata", {}).get("verification_status")
        if verification_status == "verified":
            return EvidenceLevel.VERIFIED.value
        
        return EvidenceLevel.STANDARD.value
    
    def determine_verification_status(self, validation_result: Dict) -> str:
        """Bestimmt den Verifizierungsstatus"""
        if not validation_result["is_valid"]:
            return VerificationStatus.REJECTED.value
        
        # Prüfe ob alle Validierungsprüfungen bestanden wurden
        critical_checks = ["integrity", "chain_of_custody", "legal_compliance"]
        all_critical_passed = all(
            validation_result["validation_checks"].get(check, {}).get("passed", False)
            for check in critical_checks
        )
        
        if all_critical_passed:
            return VerificationStatus.CONFIRMED.value
        else:
            return VerificationStatus.VERIFIED.value
    
    def create_validation_summary(self) -> Dict:
        """Erstellt Zusammenfassung der Validierungsergebnisse"""
        total = self.validation_stats["total_evidence_files"]
        valid = self.validation_stats["valid_evidence"]
        invalid = self.validation_stats["invalid_evidence"]
        compromised = self.validation_stats["compromised_evidence"]
        
        return {
            "total_evidence_files": total,
            "valid_evidence": valid,
            "invalid_evidence": invalid,
            "compromised_evidence": compromised,
            "validation_rate": f"{(valid/total*100):.2f}%" if total > 0 else "0%",
            "compromise_rate": f"{(compromised/total*100):.2f}%" if total > 0 else "0%",
            "validation_errors": len(self.validation_stats["validation_errors"])
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generiert Empfehlungen basierend auf Validierungsergebnissen"""
        recommendations = []
        
        if self.validation_stats["compromised_evidence"] > 0:
            recommendations.append(
                f"KRITISCH: {self.validation_stats['compromised_evidence']} Evidenz-Dateien kompromittiert - sofortige Untersuchung erforderlich"
            )
        
        if self.validation_stats["invalid_evidence"] > 0:
            recommendations.append(
                f"{self.validation_stats['invalid_evidence']} Evidenz-Dateien ungültig - Überprüfung der Sammlungsprozesse erforderlich"
            )
        
        validation_rate = (self.validation_stats["valid_evidence"] / max(1, self.validation_stats["total_evidence_files"])) * 100
        if validation_rate < 95:
            recommendations.append(
                f"Validierungsrate ({validation_rate:.1f}%) unter 95% - Prozessverbesserung erforderlich"
            )
        
        if len(self.validation_stats["validation_errors"]) > 0:
            recommendations.append(
                f"{len(self.validation_stats['validation_errors'])} Validierungsfehler aufgetreten - technische Überprüfung erforderlich"
            )
        
        return recommendations
    
    def save_validation_report(self, validation_results: Dict):
        """Speichert den Validierungsbericht"""
        report_filename = f"forensic_validation_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = self.log_dir / report_filename
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(validation_results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Validierungsbericht gespeichert: {report_filename}")
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern des Validierungsberichts: {e}")

def main():
    """Hauptfunktion für forensische Validierung"""
    base_dir = Path(__file__).parent
    evidence_dir = base_dir / "web_data"
    log_dir = base_dir / "logs"
    
    print("=== Forensischer Evidenz-Validator ===")
    print("Wissenschaftliche Gütesicherung für digitale Beweise")
    
    validator = ForensicEvidenceValidator(evidence_dir, log_dir)
    
    try:
        results = validator.validate_all_evidence()
        
        print(f"\n=== VALIDIERUNGSERGEBNISSE ===")
        summary = results["summary"]
        print(f"Gesamt-Evidenz-Dateien: {summary['total_evidence_files']}")
        print(f"Valid Evidenz: {summary['valid_evidence']}")
        print(f"Invalid Evidenz: {summary['invalid_evidence']}")
        print(f"Kompromittierte Evidenz: {summary['compromised_evidence']}")
        print(f"Validierungsrate: {summary['validation_rate']}")
        
        if results["recommendations"]:
            print(f"\n=== EMPFEHLUNGEN ===")
            for i, rec in enumerate(results["recommendations"], 1):
                print(f"{i}. {rec}")
        
        print(f"\nValidierungsbericht gespeichert in: {log_dir}")
        
    except Exception as e:
        print(f"Fehler bei der forensischen Validierung: {e}")

if __name__ == "__main__":
    main()
