from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from django.db import models
from django.db.models import Exists, OuterRef
from django.utils import timezone
from django.shortcuts import get_object_or_404
from apps.core.models import User
from apps.core.utils import create_notification, broadcast_dashboard_update
from apps.core.tasks import send_email_task
from apps.student.models import StudentNarrativeReport
from apps.student.serializers import StudentNarrativeReportSerializer
from .models import OJTProgram, OJTApplication, Attendance, SiteAssignment, Site, FlagRecord
from .serializers import OJTProgramSerializer, OJTApplicationSerializer, AttendanceSerializer, SiteAssignmentSerializer, FlagRecordSerializer, SiteApprovalSerializer


class IsCoordinator(permissions.BasePermission):
    """Permission check for coordinators."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_coordinator()
    
    def has_object_permission(self, request, view, obj):
        """Check if coordinator owns the object."""
        if request.user.is_admin():
            return True
        # Handle OJTApplication - check if coordinator owns the program
        if hasattr(obj, 'program') and hasattr(obj.program, 'coordinator'):
            return obj.program.coordinator == request.user
        # Handle other objects that have a direct coordinator field
        if hasattr(obj, 'coordinator'):
            return obj.coordinator == request.user
        return False


class OJTProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for OJT Program management."""
    serializer_class = OJTProgramSerializer
    permission_classes = [IsCoordinator]
    filterset_fields = ['status']
    search_fields = ['name']
    pagination_class = None
    
    def get_queryset(self):
        """Filter programs by coordinator."""
        user = self.request.user
        if user.is_admin():
            return OJTProgram.objects.all()
        return OJTProgram.objects.filter(coordinator=user)
    
    def perform_create(self, serializer):
        """Set coordinator to current user on creation and notify all admins."""
        program = serializer.save(coordinator=self.request.user, created_by=self.request.user)
        try:
            admins = User.objects.filter(role='admin', is_active=True)
            for admin in admins:
                create_notification(
                    recipient=admin,
                    title='New OJT Program Added',
                    message=f'A new OJT program "{program.name}" has been added by {self.request.user.get_full_name() or self.request.user.email}.',
                    type='general',
                    related_object=program,
                    related_object_type='new_program',
                )
        except Exception:
            pass
    
    def perform_update(self, serializer):
        """Save program updates."""
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """Get all applications for a program."""
        program = self.get_object()
        applications = program.applications.all()
        serializer = OJTApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class OJTApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for OJT Application management."""
    serializer_class = OJTApplicationSerializer
    permission_classes = [IsCoordinator]
    filterset_fields = ['status', 'program']
    search_fields = ['student__username', 'program__name']
    
    def get_queryset(self):
        """Filter applications by coordinator's programs."""
        user = self.request.user
        if user.is_admin():
            return OJTApplication.objects.all().select_related('student', 'program')
        return OJTApplication.objects.filter(
            program__coordinator=user
        ).select_related('student', 'program')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an application."""
        application = self.get_object()
        application.status = 'approved'
        application.approved_date = timezone.now()
        application.save()

        # Auto-assign to preferred site if one was selected
        if application.preferred_site and not SiteAssignment.objects.filter(
            student=application.student, program=application.program
        ).exists():
            SiteAssignment.objects.create(
                student=application.student,
                program=application.program,
                site=application.preferred_site,
                supervisor_name=application.preferred_site.supervisor_name,
                supervisor_contact=application.preferred_site.contact_number,
            )

        try:
            student_name = application.student.get_full_name() or application.student.username
            send_email_task.delay(
                recipient_email=application.student.email,
                subject='OJT Application Approved',
                message=f'Your OJT application for {application.program.name} has been approved.',
                title='Application Approved',
                recipient_name=student_name,
            )
        except Exception:
            pass
        broadcast_dashboard_update('applications', data={'action': 'update', 'item': OJTApplicationSerializer(application).data})
        return Response({'message': 'Application approved'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an application."""
        application = self.get_object()
        application.status = 'rejected'
        application.rejection_reason = request.data.get('reason', '')
        application.save()
        reason = request.data.get('reason', 'No reason provided')
        try:
            student_name = application.student.get_full_name() or application.student.username
            send_email_task.delay(
                recipient_email=application.student.email,
                subject='OJT Application Rejected',
                message=f'Your OJT application for {application.program.name} has been rejected. Reason: {reason}',
                title='Application Rejected',
                recipient_name=student_name,
            )
        except Exception:
            pass
        broadcast_dashboard_update('applications', data={'action': 'update', 'item': OJTApplicationSerializer(application).data})
        return Response({'message': 'Application rejected'}, status=status.HTTP_200_OK)


class AttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Attendance management."""
    serializer_class = AttendanceSerializer
    permission_classes = [IsCoordinator]
    throttle_classes = [UserRateThrottle]
    filterset_fields = ['program', 'student', 'date']
    search_fields = ['student__username']
    
    def get_queryset(self):
        """Filter attendance records by coordinator's programs."""
        user = self.request.user
        if user.is_admin():
            return Attendance.objects.all().select_related('student', 'program')
        return Attendance.objects.filter(
            program__coordinator=user
        ).select_related('student', 'program')
    
    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        """Clock in for attendance."""
        student_id = request.data.get('student_id')
        program_id = request.data.get('program_id')

        if not student_id or not program_id:
            return Response({'error': 'student_id and program_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the program belongs to this coordinator (or user is admin)
        program = get_object_or_404(OJTProgram, id=program_id)
        if not request.user.is_admin() and program.coordinator != request.user:
            return Response({'error': 'You do not have access to this program'}, status=status.HTTP_403_FORBIDDEN)

        # Verify the student has an approved application for this program
        if not OJTApplication.objects.filter(student_id=student_id, program_id=program_id, status='approved').exists():
            return Response({'error': 'Student does not have an approved application for this program'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.localtime(timezone.now())
        now_time = now.time()
        hour = now.hour
        is_am = hour < 12

        attendance, created = Attendance.objects.get_or_create(
            student_id=student_id,
            program_id=program_id,
            date=timezone.now().date(),
            defaults={
                'latitude': request.data.get('latitude'),
                'longitude': request.data.get('longitude'),
                'ip_address': request.META.get('REMOTE_ADDR'),
            }
        )

        if is_am:
            if attendance.time_in_am is not None:
                return Response({'error': 'Already clocked in for AM session today'}, status=status.HTTP_400_BAD_REQUEST)
            attendance.time_in = now_time
            attendance.time_in_am = now_time
        else:
            if attendance.time_in_pm is not None:
                return Response({'error': 'Already clocked in for PM session today'}, status=status.HTTP_400_BAD_REQUEST)
            attendance.time_in = now_time
            attendance.time_in_pm = now_time
        attendance.save()
        
        if created:
            student = attendance.student
            program = attendance.program
            if program.coordinator and program.coordinator != request.user:
                coordinator_name = request.user.get_full_name() or request.user.username
                create_notification(
                    recipient=program.coordinator,
                    title='Student Clocked In',
                    message=f'{student.get_full_name() or student.username} has clocked in for {program.name}.',
                    type='general',
                    related_object=attendance,
                    related_object_type='Attendance',
                )
        
        serializer = self.get_serializer(attendance)
        broadcast_dashboard_update('attendance', data={'action': 'create', 'item': serializer.data})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def clock_out(self, request, pk=None):
        """Clock out for attendance."""
        attendance = self.get_object()
        now = timezone.localtime(timezone.now())
        now_time = now.time()
        hour = now.hour
        is_am = hour < 12

        if is_am:
            if attendance.time_in_am is None:
                return Response({'error': 'No AM clock-in found for today'}, status=status.HTTP_400_BAD_REQUEST)
            if attendance.time_out_am is not None:
                return Response({'error': 'Already clocked out for AM session today'}, status=status.HTTP_400_BAD_REQUEST)
            attendance.time_out = now_time
            attendance.time_out_am = now_time
        else:
            if attendance.time_in_pm is None:
                return Response({'error': 'No PM clock-in found for today'}, status=status.HTTP_400_BAD_REQUEST)
            if attendance.time_out_pm is not None:
                return Response({'error': 'Already clocked out for PM session today'}, status=status.HTTP_400_BAD_REQUEST)
            attendance.time_out = now_time
            attendance.time_out_pm = now_time

        attendance.save()
        
        student = attendance.student
        program = attendance.program
        if program.coordinator and program.coordinator != request.user:
            coordinator_name = request.user.get_full_name() or request.user.username
            create_notification(
                recipient=program.coordinator,
                title='Student Clocked Out',
                message=f'{student.get_full_name() or student.username} has clocked out for {program.name}.',
                type='general',
                related_object=attendance,
                related_object_type='Attendance',
            )

        serializer = self.get_serializer(attendance)
        broadcast_dashboard_update('attendance', data={'action': 'update', 'item': serializer.data})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CoordinatorDashboardViewSet(viewsets.ViewSet):
    """ViewSet for coordinator dashboard operations."""
    permission_classes = [IsCoordinator]
    
    @action(detail=False, methods=['get'], url_path='my-students')
    def my_students(self, request):
        """Get all approved students for this coordinator's course and programs."""
        coordinator = request.user

        coordinator_course = coordinator.course
        students = User.objects.filter(
            role='student',
            approval_status='approved',
            ojt_applications__status='approved',
            ojt_applications__program__coordinator=coordinator
        )

        if coordinator_course:
            students = students.filter(student_profile__course=coordinator_course)

        students = students.select_related('student_profile__course').distinct().order_by('-created_at')

        exclude_assigned = request.query_params.get('exclude_assigned') == 'true'
        if exclude_assigned:
            students = students.annotate(
                has_assignment=Exists(
                    SiteAssignment.objects.filter(
                        student=OuterRef('pk')
                    )
                )
            ).filter(has_assignment=False)
        
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'name': student.get_full_name(),
                'email': student.email,
                'username': student.username,
                'course': student.student_profile.course.name if hasattr(student, 'student_profile') and student.student_profile and student.student_profile.course else None,
                'student_id': student.student_profile.student_id if hasattr(student, 'student_profile') and student.student_profile else None,
            })
        
        return Response(students_data)
    
    @action(detail=False, methods=['get'], url_path='student-accounts')
    def student_accounts(self, request):
        """Get student accounts with attendance data for this coordinator's course."""
        from datetime import date, datetime, time, timedelta

        coordinator = request.user
        students = User.objects.filter(
            role='student'
        ).exclude(
            approval_status='pending'
        ).filter(
            ojt_applications__program__coordinator=coordinator,
            ojt_applications__status='approved'
        )
        coordinator_course = coordinator.course
        if coordinator_course:
            students = students.filter(student_profile__course=coordinator_course)
        students = students.select_related('student_profile').distinct().order_by('-created_at')

        today = date.today()
        att_qs = Attendance.objects.filter(student__in=students).select_related('student')

        stats = {}
        for att in att_qs:
            sid = att.student_id
            if sid not in stats:
                stats[sid] = {'present_days': 0, 'total_seconds': 0, 'today_status': '', 'last_attendance': None}
            stats[sid]['present_days'] += 1
            if stats[sid]['last_attendance'] is None or att.date > stats[sid]['last_attendance']:
                stats[sid]['last_attendance'] = att.date
            if att.time_out:
                tin = datetime.combine(att.date, att.time_in)
                tout = datetime.combine(att.date, att.time_out)
                stats[sid]['total_seconds'] += (tout - tin).total_seconds()
            if att.date == today:
                overall = att.get_overall_status()
                if overall == 'completed':
                    stats[sid]['today_status'] = 'present'
                elif overall == 'partial':
                    stats[sid]['today_status'] = 'on-going'
                else:
                    stats[sid]['today_status'] = 'on-going'

        students_data = []
        for student in students:
            s = stats.get(student.id, {'present_days': 0, 'total_seconds': 0, 'today_status': '', 'last_attendance': None})
            if not s['today_status']:
                s['today_status'] = 'absent'
            hours = round(s['total_seconds'] / 3600, 2)
            # ponytail: count weekdays from account creation to today (matches student calendar logic)
            acct_start = student.date_joined.date() if student.date_joined else today
            working_days = sum(1 for i in range((today - acct_start).days + 1) if (acct_start + timedelta(days=i)).weekday() < 5)
            absent_days = max(0, working_days - s['present_days'])
            students_data.append({
                'id': student.id,
                'name': student.get_full_name(),
                'email': student.email,
                'student_id': student.student_profile.student_id if hasattr(student, 'student_profile') and student.student_profile else None,
                'is_active': student.is_active,
                'created_at': student.created_at,
                'present_days': s['present_days'],
                'absent_days': absent_days,
                'total_hours': hours,
                'today_status': s['today_status'],
                'last_attendance': s['last_attendance'].isoformat() if s['last_attendance'] else None,
            })

        return Response(students_data)

    @action(detail=False, methods=['post'], url_path='approve-student')
    def approve_student(self, request):
        """Approve a student application."""
        app_id = request.data.get('app_id')
        application = get_object_or_404(OJTApplication, id=app_id, program__coordinator=request.user)
        
        application.status = 'approved'
        application.approved_date = timezone.now()
        application.save()

        # Auto-assign to preferred site if one was selected
        if application.preferred_site and not SiteAssignment.objects.filter(
            student=application.student, program=application.program
        ).exists():
            SiteAssignment.objects.create(
                student=application.student,
                program=application.program,
                site=application.preferred_site,
                supervisor_name=application.preferred_site.supervisor_name,
                supervisor_contact=application.preferred_site.contact_number,
            )

        broadcast_dashboard_update('applications', data={'action': 'update', 'item': OJTApplicationSerializer(application).data})
        return Response({'message': 'Student approved successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='reject-student')
    def reject_student(self, request):
        """Reject a student application."""
        app_id = request.data.get('app_id')
        reason = request.data.get('reason', '')
        application = get_object_or_404(OJTApplication, id=app_id, program__coordinator=request.user)
        
        application.status = 'rejected'
        application.rejection_reason = reason
        application.save()

        broadcast_dashboard_update('applications', data={'action': 'update', 'item': OJTApplicationSerializer(application).data})
        return Response({'message': 'Student rejected'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='attendance-records')
    def attendance_records(self, request):
        """Get attendance records for coordinator's students."""
        coordinator = request.user
        program_id = request.query_params.get('program_id')
        student_id = request.query_params.get('student_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        programs = OJTProgram.objects.filter(coordinator=coordinator)
        if program_id:
            programs = programs.filter(id=program_id)

        attendances = Attendance.objects.filter(
            program__in=programs
        ).select_related('student', 'program').order_by('-date', 'time_in')

        if student_id:
            attendances = attendances.filter(student_id=student_id)
        if date_from:
            attendances = attendances.filter(date__gte=date_from)
        if date_to:
            attendances = attendances.filter(date__lte=date_to)

        records = []
        for att in attendances:
            records.append({
                'id': att.id,
                'student_id': att.student.id,
                'student_name': att.student.get_full_name(),
                'program_id': att.program.id,
                'program_name': att.program.name,
                'date': att.date,
                'time_in': str(att.time_in)[:5] if att.time_in else '—',
                'time_out': str(att.time_out)[:5] if att.time_out else '—',
                'time_in_am': str(att.time_in_am)[:5] if att.time_in_am else '—',
                'time_out_am': str(att.time_out_am)[:5] if att.time_out_am else '—',
                'time_in_pm': str(att.time_in_pm)[:5] if att.time_in_pm else '—',
                'time_out_pm': str(att.time_out_pm)[:5] if att.time_out_pm else '—',
                'am_status': att.get_am_status(),
                'pm_status': att.get_pm_status(),
                'status': att.get_overall_status(),
                'facial_recognition_used': att.facial_recognition_used,
                'notes': att.notes,
            })

        return Response(records)

    @action(detail=False, methods=['get'], url_path='student-narratives')
    def student_narratives(self, request):
        """Get student-submitted narratives filtered by coordinator's course."""
        coordinator = request.user

        # Get approved students in coordinator's programs
        applications = OJTApplication.objects.filter(
            program__coordinator=coordinator,
            status='approved'
        ).select_related('student', 'program')

        coordinator_course = coordinator.course
        if coordinator_course:
            applications = applications.filter(
                student__student_profile__course=coordinator_course
            )

        student_ids = applications.values_list('student_id', flat=True)

        narratives = StudentNarrativeReport.objects.filter(
            student_id__in=student_ids
        ).select_related('student', 'program').order_by('-log_date')

        serializer = StudentNarrativeReportSerializer(narratives, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='grade-narrative')
    def grade_narrative(self, request):
        """Grade a student narrative report."""
        narrative_id = request.data.get('narrative_id')
        grade = request.data.get('grade')
        feedback = request.data.get('feedback', '')

        if not narrative_id:
            return Response({'error': 'narrative_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        if grade is None or not isinstance(grade, int) or grade < 1 or grade > 100:
            return Response({'error': 'Grade must be an integer between 1 and 100'}, status=status.HTTP_400_BAD_REQUEST)

        narrative = get_object_or_404(StudentNarrativeReport, id=narrative_id)
        narrative.grade = grade
        narrative.feedback = feedback
        narrative.graded_by = request.user
        narrative.graded_at = timezone.now()
        narrative.save(update_fields=['grade', 'feedback', 'graded_by', 'graded_at'])

        student_name = narrative.student.get_full_name() or narrative.student.username
        send_email_task.delay(
            recipient_email=narrative.student.email,
            subject='Narrative Report Graded',
            message=f'Your narrative report for {narrative.log_date} has been graded: {grade}/100. Feedback: {feedback or "None provided"}',
            title='Report Graded',
            recipient_name=student_name,
        )

        serializer = StudentNarrativeReportSerializer(narrative)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='available-sites')
    def available_sites(self, request):
        """Get sites filtered by coordinator's course."""
        coordinator = request.user
        if coordinator.course:
            sites = Site.objects.filter(
                models.Q(course=coordinator.course) | models.Q(course__isnull=True),
                is_active=True
            ).order_by('name')
        else:
            sites = Site.objects.filter(is_active=True).order_by('name')
        data = [{
            'id': str(s.id),
            'name': s.name,
            'supervisor_name': s.supervisor_name,
            'contact_number': s.contact_number,
        } for s in sites]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='flagged-records')
    def flagged_records(self, request):
        """Get all unresolved flagged attendance records."""
        coordinator = request.user
        programs = OJTProgram.objects.filter(coordinator=coordinator)
        flags = FlagRecord.objects.filter(
            resolved=False,
            attendance__program__in=programs
        ).select_related('attendance', 'attendance__student', 'attendance__program', 'resolved_by')
        serializer = FlagRecordSerializer(flags, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='resolve-flag')
    def resolve_flag(self, request, pk=None):
        """Resolve a flagged record."""
        flag = get_object_or_404(FlagRecord, id=pk)
        flag.resolved = True
        flag.resolved_by = request.user
        flag.resolved_at = timezone.now()
        flag.save(update_fields=['resolved', 'resolved_by', 'resolved_at'])
        broadcast_dashboard_update('flags', data={'action': 'update', 'item': FlagRecordSerializer(flag).data})
        return Response({'message': 'Flag resolved'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='report/csv')
    def report_csv(self, request):
        """Export attendance CSV for coordinator's students."""
        import csv
        from django.http import HttpResponse

        coordinator = request.user
        programs = OJTProgram.objects.filter(coordinator=coordinator)
        attendances = Attendance.objects.filter(
            program__in=programs
        ).select_related('student', 'program').order_by('-date', 'student__username')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_report_{timezone.now().date()}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Student', 'Program', 'Date', 'AM Time In', 'AM Time Out', 'PM Time In', 'PM Time Out', 'AM Status', 'PM Status', 'Overall Status', 'Facial Recognition', 'Notes'])
        for att in attendances:
            writer.writerow([
                att.student.get_full_name() or att.student.username,
                att.program.name,
                att.date,
                str(att.time_in_am)[:5] if att.time_in_am else '',
                str(att.time_out_am)[:5] if att.time_out_am else '',
                str(att.time_in_pm)[:5] if att.time_in_pm else '',
                str(att.time_out_pm)[:5] if att.time_out_pm else '',
                att.get_am_status(),
                att.get_pm_status(),
                att.get_overall_status(),
                'Yes' if att.facial_recognition_used else 'No',
                att.notes or '',
            ])
        return response

    @action(detail=False, methods=['get'], url_path='report/stats')
    def report_stats(self, request):
        """Get aggregate stats for coordinator's programs."""
        coordinator = request.user
        programs = OJTProgram.objects.filter(coordinator=coordinator)

        total_students = OJTApplication.objects.filter(
            program__in=programs, status='approved'
        ).values('student').distinct().count()

        today = timezone.now().date()
        total_attendances = Attendance.objects.filter(program__in=programs, date=today).count()
        total_hours = 0
        for att in Attendance.objects.filter(program__in=programs, time_out__isnull=False):
            from datetime import datetime as dt
            if att.time_in:
                tin = dt.combine(att.date, att.time_in)
                tout = dt.combine(att.date, att.time_out)
                total_hours += (tout - tin).total_seconds() / 3600
            else:
                am_hours = 0
                pm_hours = 0
                if att.time_in_am and att.time_out_am:
                    am_hours = (dt.combine(att.date, att.time_out_am) - dt.combine(att.date, att.time_in_am)).total_seconds() / 3600
                if att.time_in_pm and att.time_out_pm:
                    pm_hours = (dt.combine(att.date, att.time_out_pm) - dt.combine(att.date, att.time_in_pm)).total_seconds() / 3600
                total_hours += am_hours + pm_hours

        pending_applications = OJTApplication.objects.filter(
            program__in=programs, status='pending'
        ).count()

        flagged_count = FlagRecord.objects.filter(
            resolved=False, attendance__program__in=programs
        ).count()

        return Response({
            'total_students': total_students,
            'attendances_today': total_attendances,
            'total_hours_logged': round(total_hours, 1),
            'pending_applications': pending_applications,
            'flagged_records': flagged_count,
            'active_programs': programs.filter(status='active').count(),
        })


class SiteAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Site Assignment management."""
    serializer_class = SiteAssignmentSerializer
    permission_classes = [IsCoordinator]
    pagination_class = None

    def get_queryset(self):
        coordinator = self.request.user
        return SiteAssignment.objects.filter(
            program__coordinator=coordinator
        ).select_related('student', 'program', 'site')

    @action(detail=False, methods=['get'], url_path='my-site')
    def my_site(self, request):
        """Get the site assigned to this coordinator by admin."""
        from .models import Site
        site = Site.objects.filter(coordinator=request.user, is_active=True).first()
        if not site:
            return Response({'error': 'No site assigned'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'id': site.id,
            'name': site.name,
            'supervisor_name': site.supervisor_name,
            'contact_number': site.contact_number,
        })

    @action(detail=False, methods=['get'], url_path='by-student')
    def by_student(self, request):
        """Get site assignment for a specific student."""
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response({'error': 'student_id required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            assignment = self.get_queryset().get(student_id=student_id)
            serializer = self.get_serializer(assignment)
            return Response(serializer.data)
        except SiteAssignment.DoesNotExist:
            return Response({'error': 'No assignment found'}, status=status.HTTP_404_NOT_FOUND)


class SiteApprovalViewSet(viewsets.ViewSet):
    """ViewSet for coordinator site approval (pending sites only)."""
    permission_classes = [IsCoordinator]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return Site.objects.filter(
            status='pending', is_active=True,
            coordinator=user,
        ).select_related('course')

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        """List pending sites assigned to this coordinator."""
        sites = self.get_queryset()
        serializer = SiteApprovalSerializer(sites, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='all')
    def all_sites(self, request):
        """List all sites assigned to this coordinator (any status)."""
        user = request.user
        sites = Site.objects.filter(
            coordinator=user, is_active=True
        ).select_related('course').order_by('-created_at')
        serializer = SiteApprovalSerializer(sites, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Approve a pending site."""
        site = self.get_object()
        if site.status != 'pending':
            return Response(
                {'error': f'Cannot approve a site that is already "{site.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        site.status = 'approved'
        site.save(update_fields=['status', 'updated_at'])
        broadcast_dashboard_update('sites', data={'action': 'update', 'item': SiteApprovalSerializer(site).data})
        return Response({'message': f'Site "{site.name}" approved.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Reject a pending site with a reason."""
        site = self.get_object()
        if site.status != 'pending':
            return Response(
                {'error': f'Cannot reject a site that is already "{site.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get('rejection_reason', '').strip()
        if not reason:
            return Response(
                {'error': 'rejection_reason is required when rejecting a site.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        site.status = 'rejected'
        site.rejection_reason = reason
        site.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        broadcast_dashboard_update('sites', data={'action': 'update', 'item': SiteApprovalSerializer(site).data})
        return Response({'message': f'Site "{site.name}" rejected.'}, status=status.HTTP_200_OK)
