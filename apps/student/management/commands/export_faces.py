import os
import pickle
import cv2
import numpy as np
from pathlib import Path
from django.core.management.base import BaseCommand
from apps.student.models import FacialRecognition


class Command(BaseCommand):
    help = 'Export all enrolled face images as PNG files'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='exported_faces', help='Output directory')

    def handle(self, *args, **options):
        out_dir = Path(options['output'])
        out_dir.mkdir(exist_ok=True)

        records = FacialRecognition.objects.select_related('student').all()
        if not records.exists():
            self.stdout.write(self.style.WARNING('No facial records found'))
            return

        count = 0
        for rec in records:
            try:
                face = pickle.loads(rec.facial_encoding)
                filename = f"{rec.student.username}.png"
                cv2.imwrite(str(out_dir / filename), face)
                count += 1
                self.stdout.write(f'  Saved: {filename}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Failed: {rec.student.username} — {e}'))

        self.stdout.write(self.style.SUCCESS(f'Done. {count} face(s) exported to {out_dir}/'))
