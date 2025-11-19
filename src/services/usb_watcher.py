#!/usr/bin/env python3
"""
USB Docking Station Watcher for Grok Doc v2.0
Monitors USB devices for medical data and triggers automated processing

Monitors:
- DICOM files (X-rays, CTs, MRIs) → MONAI/CheXNet analysis
- CSV files (lab results) → XGBoost predictions
- PDF files (external reports) → scispaCy NLP extraction

Workflow:
1. USB device plugged in
2. Detect new files via watchdog
3. Copy to hospital server
4. Trigger appropriate AI pipeline
5. Results auto-inserted into SOAP note
"""

import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json

# Watchdog for file system monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("WARNING: watchdog not installed. Run: pip install watchdog")

# Import medical AI pipelines
from medical_imaging import get_imaging_pipeline


class MedicalFileHandler(FileSystemEventHandler):
    """
    File system event handler for medical data

    Triggered when new files appear on USB device
    """

    def __init__(
        self,
        server_upload_path: str = "/hospital/server/incoming/",
        auto_process: bool = True
    ):
        """
        Initialize medical file handler

        Args:
            server_upload_path: Path to hospital server for uploads
            auto_process: Whether to automatically trigger AI analysis
        """
        super().__init__()
        self.server_path = Path(server_upload_path)
        self.server_path.mkdir(parents=True, exist_ok=True)
        self.auto_process = auto_process

        # Processing statistics
        self.stats = {
            'dicom_files': 0,
            'lab_files': 0,
            'pdf_files': 0,
            'errors': 0
        }

    def on_created(self, event):
        """Handle file creation event"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        file_ext = file_path.suffix.lower()

        print(f"\n{'='*60}")
        print(f"New file detected: {file_path.name}")
        print(f"Extension: {file_ext}")
        print(f"Size: {file_path.stat().st_size / 1024:.1f} KB")
        print(f"{'='*60}")

        # Route by file type
        if file_ext == '.dcm':
            self._handle_dicom(file_path)
        elif file_ext == '.csv':
            self._handle_lab_csv(file_path)
        elif file_ext == '.pdf':
            self._handle_pdf_report(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg']:
            self._handle_image(file_path)
        else:
            print(f"Ignoring unsupported file type: {file_ext}")

    def _handle_dicom(self, file_path: Path):
        """
        Process DICOM file (X-ray, CT, MRI)

        Workflow:
        1. Copy to server
        2. Trigger MONAI/CheXNet analysis
        3. Store results for Radiology Agent
        """
        print("Processing DICOM file...")

        try:
            # Copy to server
            server_file = self.server_path / "dicom" / file_path.name
            server_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, server_file)
            print(f"Copied to server: {server_file}")

            # Trigger imaging analysis
            if self.auto_process:
                imaging_pipeline = get_imaging_pipeline()

                # Detect modality from DICOM metadata
                modality = self._detect_dicom_modality(file_path)
                print(f"Detected modality: {modality}")

                # Analyze
                result = imaging_pipeline.analyze_image(str(server_file), modality=modality)

                # Save results
                results_file = server_file.with_suffix('.json')
                with open(results_file, 'w') as f:
                    json.dump(result, f, indent=2)

                print(f"Analysis complete: {result.get('findings', 'N/A')}")
                print(f"Results saved to: {results_file}")

            self.stats['dicom_files'] += 1

        except Exception as e:
            print(f"Error processing DICOM: {e}")
            self.stats['errors'] += 1

    def _handle_lab_csv(self, file_path: Path):
        """
        Process lab results CSV

        Workflow:
        1. Copy to server
        2. Parse lab values
        3. Trigger XGBoost predictions (if configured)
        4. Store for integration with SOAP note
        """
        print("Processing lab results CSV...")

        try:
            # Copy to server
            server_file = self.server_path / "labs" / file_path.name
            server_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, server_file)
            print(f"Copied to server: {server_file}")

            # Parse lab values
            if self.auto_process:
                lab_values = self._parse_lab_csv(server_file)
                print(f"Parsed {len(lab_values)} lab values")

                # Save parsed data
                results_file = server_file.with_suffix('.json')
                with open(results_file, 'w') as f:
                    json.dump(lab_values, f, indent=2)

                print(f"Lab data saved to: {results_file}")

                # TODO: Trigger XGBoost predictions
                # from lab_predictions import predict_creatinine_24h
                # prediction = predict_creatinine_24h(lab_values)

            self.stats['lab_files'] += 1

        except Exception as e:
            print(f"Error processing lab CSV: {e}")
            self.stats['errors'] += 1

    def _handle_pdf_report(self, file_path: Path):
        """
        Process PDF medical report

        Workflow:
        1. Copy to server
        2. Extract text with PyPDF2
        3. Run scispaCy NLP to extract entities
        4. Store structured data
        """
        print("Processing PDF report...")

        try:
            # Copy to server
            server_file = self.server_path / "reports" / file_path.name
            server_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, server_file)
            print(f"Copied to server: {server_file}")

            # Extract text
            if self.auto_process:
                text = self._extract_pdf_text(server_file)
                print(f"Extracted {len(text)} characters from PDF")

                # TODO: Run scispaCy NLP
                # from medical_nlp import extract_medical_entities
                # entities = extract_medical_entities(text)

                # Save text
                text_file = server_file.with_suffix('.txt')
                with open(text_file, 'w') as f:
                    f.write(text)

                print(f"Text saved to: {text_file}")

            self.stats['pdf_files'] += 1

        except Exception as e:
            print(f"Error processing PDF: {e}")
            self.stats['errors'] += 1

    def _handle_image(self, file_path: Path):
        """Handle image files (PNG, JPG) - treat as X-rays"""
        print("Processing image file as X-ray...")

        try:
            # Copy to server
            server_file = self.server_path / "images" / file_path.name
            server_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, server_file)
            print(f"Copied to server: {server_file}")

            # Trigger X-ray analysis
            if self.auto_process:
                imaging_pipeline = get_imaging_pipeline()
                result = imaging_pipeline.analyze_image(str(server_file), modality="XR")

                # Save results
                results_file = server_file.with_suffix('.json')
                with open(results_file, 'w') as f:
                    json.dump(result, f, indent=2)

                print(f"Analysis complete: {result.get('findings', 'N/A')}")

            self.stats['dicom_files'] += 1  # Count as DICOM

        except Exception as e:
            print(f"Error processing image: {e}")
            self.stats['errors'] += 1

    def _detect_dicom_modality(self, dicom_path: Path) -> str:
        """Detect imaging modality from DICOM metadata"""
        try:
            import pydicom
            dcm = pydicom.dcmread(str(dicom_path))
            modality = dcm.get('Modality', 'XR')  # Default to X-ray
            return modality
        except:
            return 'XR'  # Default to X-ray if can't read

    def _parse_lab_csv(self, csv_path: Path) -> Dict:
        """Parse lab results from CSV file"""
        import csv

        lab_values = {}

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Assuming CSV format: Test, Value, Units, Reference
                test_name = row.get('Test', '')
                value = row.get('Value', '')
                units = row.get('Units', '')

                if test_name and value:
                    lab_values[test_name] = {
                        'value': value,
                        'units': units,
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    }

        return lab_values

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from PDF"""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(pdf_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except ImportError:
            print("PyPDF2 not installed. Run: pip install PyPDF2")
            return ""
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""


class USBWatcher:
    """
    USB device monitoring service

    Watches USB mount points for new medical data files
    """

    def __init__(
        self,
        usb_mount_path: str = "/media/usb/",
        server_upload_path: str = "/hospital/server/incoming/",
        auto_start: bool = False
    ):
        """
        Initialize USB watcher

        Args:
            usb_mount_path: Where USB devices are mounted
            server_upload_path: Server path for uploads
            auto_start: Whether to start monitoring immediately
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError("watchdog required. Install with: pip install watchdog")

        self.usb_path = Path(usb_mount_path)
        self.event_handler = MedicalFileHandler(server_upload_path)
        self.observer = Observer()

        if auto_start:
            self.start()

    def start(self):
        """Start monitoring USB devices"""
        # Create USB mount point if it doesn't exist
        self.usb_path.mkdir(parents=True, exist_ok=True)

        # Schedule observer
        self.observer.schedule(
            self.event_handler,
            str(self.usb_path),
            recursive=True  # Monitor subdirectories
        )

        self.observer.start()

        print(f"\n{'='*60}")
        print("USB WATCHER STARTED")
        print(f"Monitoring: {self.usb_path}")
        print("Watching for:")
        print("  - DICOM files (.dcm) → Radiology AI")
        print("  - Lab results (.csv) → XGBoost predictions")
        print("  - Reports (.pdf) → scispaCy NLP")
        print("  - Images (.png, .jpg) → X-ray analysis")
        print(f"{'='*60}\n")

    def stop(self):
        """Stop monitoring"""
        self.observer.stop()
        self.observer.join()
        print("USB watcher stopped")

    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return self.event_handler.stats


def run_usb_watcher(
    usb_path: str = "/media/usb/",
    server_path: str = "/hospital/server/incoming/"
):
    """
    Run USB watcher service (blocking)

    Args:
        usb_path: USB mount point
        server_path: Server upload directory
    """

    watcher = USBWatcher(usb_path, server_path, auto_start=True)

    try:
        print("USB watcher running. Press Ctrl+C to stop.")
        while True:
            time.sleep(10)

            # Print stats every 10 seconds
            stats = watcher.get_stats()
            if any(stats.values()):
                print(f"Stats: DICOM={stats['dicom_files']}, Labs={stats['lab_files']}, "
                      f"PDFs={stats['pdf_files']}, Errors={stats['errors']}")

    except KeyboardInterrupt:
        print("\nStopping USB watcher...")
        watcher.stop()


if __name__ == "__main__":
    # Run USB watcher service
    print("Grok Doc USB Watcher v2.0")
    print(f"Watchdog available: {WATCHDOG_AVAILABLE}")

    if WATCHDOG_AVAILABLE:
        # Use temporary test directory
        test_usb = "/tmp/grok_usb_test/"
        test_server = "/tmp/grok_server_test/"

        print(f"\nTest mode: Monitoring {test_usb}")
        print("Drop DICOM, CSV, or PDF files here to test automatic processing\n")

        run_usb_watcher(test_usb, test_server)
    else:
        print("\nInstall watchdog to enable USB monitoring:")
        print("  pip install watchdog")
