"""
Admin panel - Xodimlar boshqaruvi API
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from asgiref.sync import sync_to_async
from functools import wraps
import json

from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.bot import District, Region


def async_view(func):
    """Decorator to make sync views async"""
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        return await func(request, *args, **kwargs)
    return wrapper


def admin_required(func):
    """Admin tekshirish decorator"""
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        tg_id = request.GET.get('tg_id')
        if not tg_id:
            return JsonResponse({'error': 'tg_id required'}, status=400)
        
        try:
            user = await sync_to_async(TelegramUser.objects.get)(user_id=int(tg_id))
            if not (user.is_admin or user.role == 'admin'):
                return JsonResponse({'error': 'Admin access required'}, status=403)
        except TelegramUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        return await func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@require_http_methods(["GET"])
@async_view
@admin_required
async def list_staff(request):
    """
    Xodimlar ro'yxati (Admin, Courier, Doctor)
    
    Query params:
    - tg_id: admin user ID (required)
    - role: filter by role (admin, courier, doctor) - optional
    - page: sahifa raqami (default: 1)
    - search: qidiruv (optional)
    """
    role_filter = request.GET.get('role', 'all')
    page = int(request.GET.get('page', 1))
    search = request.GET.get('search', '').strip()
    
    # Base queryset
    queryset = TelegramUser.objects.filter(
        role__in=['admin', 'courier', 'doctor']
    ).select_related('district', 'district__region').order_by('-date_joined')
    
    # Role filter
    if role_filter != 'all':
        queryset = queryset.filter(role=role_filter)
    
    # Search filter
    if search:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(first_name__icontains=search) |
            Q(username__icontains=search) |
            Q(user_id__icontains=search)
        )
    
    # Convert to list for pagination
    staff_list = await sync_to_async(list)(queryset)
    
    # Pagination
    paginator = Paginator(staff_list, 50)
    page_obj = paginator.get_page(page)
    
    # Serialize data
    staff_data = []
    for staff in page_obj:
        district_name = staff.district.name if staff.district else None
        region_name = staff.district.region.name if staff.district and staff.district.region else None
        
        staff_data.append({
            'id': staff.id,
            'user_id': staff.user_id,
            'first_name': staff.first_name or 'N/A',
            'username': staff.username,
            'role': staff.role,
            'is_admin': staff.is_admin,
            'is_active': staff.is_active,
            'district_id': staff.district.id if staff.district else None,
            'district_name': district_name,
            'region_name': region_name,
            'phone': staff.phone_number,
            'lang': staff.lang,
            'date_joined': staff.date_joined.isoformat() if staff.date_joined else None,
        })
    
    return JsonResponse({
        'success': True,
        'staff': staff_data,
        'pagination': {
            'page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })


@csrf_exempt
@require_http_methods(["GET"])
@async_view
@admin_required
async def get_staff_detail(request, staff_id):
    """
    Xodim batafsil ma'lumoti
    """
    try:
        staff = await sync_to_async(
            TelegramUser.objects.select_related('district', 'district__region').get
        )(id=staff_id)
        
        data = {
            'id': staff.id,
            'user_id': staff.user_id,
            'first_name': staff.first_name,
            'username': staff.username,
            'role': staff.role,
            'is_admin': staff.is_admin,
            'is_active': staff.is_active,
            'district': {
                'id': staff.district.id if staff.district else None,
                'name': staff.district.name if staff.district else None,
                'region_name': staff.district.region.name if staff.district and staff.district.region else None,
            } if staff.district else None,
            'phone': staff.phone_number,
            'lang': staff.lang,
            'date_joined': staff.date_joined.isoformat() if staff.date_joined else None,
            'patient_id': staff.patient_id,
            'bonus_points': staff.bonus_points,
            'order_count': staff.order_count,
        }
        
        return JsonResponse({'success': True, 'staff': data})
        
    except TelegramUser.DoesNotExist:
        return JsonResponse({'error': 'Staff not found'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
@async_view
@admin_required
async def update_staff_role(request):
    """
    Xodim rolini o'zgartirish
    
    POST data:
    - staff_id: xodim ID
    - role: yangi rol (user, courier, doctor, admin)
    """
    try:
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        new_role = data.get('role')
        
        if not staff_id or not new_role:
            return JsonResponse({'error': 'staff_id and role required'}, status=400)
        
        if new_role not in ['user', 'courier', 'doctor', 'admin']:
            return JsonResponse({'error': 'Invalid role'}, status=400)
        
        staff = await sync_to_async(TelegramUser.objects.get)(id=staff_id)
        old_role = staff.role
        
        staff.role = new_role
        
        # Admin rol uchun is_admin flagni o'zgartirish
        if new_role == 'admin':
            staff.is_admin = True
        elif old_role == 'admin':
            staff.is_admin = False
        
        await sync_to_async(staff.save)(update_fields=['role', 'is_admin'])
        
        return JsonResponse({
            'success': True,
            'message': 'Role updated successfully',
            'staff': {
                'id': staff.id,
                'user_id': staff.user_id,
                'first_name': staff.first_name,
                'role': staff.role,
                'is_admin': staff.is_admin,
            }
        })
        
    except TelegramUser.DoesNotExist:
        return JsonResponse({'error': 'Staff not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@async_view
@admin_required
async def assign_courier_district(request):
    """
    Kuryerga tuman tayinlash
    
    POST data:
    - courier_id: kuryer ID
    - district_id: tuman ID
    """
    try:
        data = json.loads(request.body)
        courier_id = data.get('courier_id')
        district_id = data.get('district_id')
        
        if not courier_id:
            return JsonResponse({'error': 'courier_id required'}, status=400)
        
        courier = await sync_to_async(TelegramUser.objects.get)(id=courier_id)
        
        if courier.role != 'courier':
            return JsonResponse({'error': 'User is not a courier'}, status=400)
        
        if district_id:
            try:
                district = await sync_to_async(District.objects.get)(id=district_id)
                courier.district = district
            except District.DoesNotExist:
                return JsonResponse({'error': 'District not found'}, status=404)
        else:
            courier.district = None
        
        await sync_to_async(courier.save)(update_fields=['district'])
        
        return JsonResponse({
            'success': True,
            'message': 'District assigned successfully',
            'courier': {
                'id': courier.id,
                'user_id': courier.user_id,
                'first_name': courier.first_name,
                'district': {
                    'id': courier.district.id if courier.district else None,
                    'name': courier.district.name if courier.district else None,
                } if courier.district else None,
            }
        })
        
    except TelegramUser.DoesNotExist:
        return JsonResponse({'error': 'Courier not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@async_view
@admin_required
async def get_districts_list(request):
    """
    Barcha tumanlar ro'yxati
    """
    districts = await sync_to_async(
        lambda: list(
            District.objects.select_related('region')
            .filter(is_active=True)
            .values('id', 'name', 'region__name', 'delivery_price')
            .order_by('region__name', 'name')
        )
    )()
    
    districts_data = [
        {
            'id': d['id'],
            'name': d['name'],
            'region_name': d['region__name'],
            'delivery_price': d['delivery_price'],
        }
        for d in districts
    ]
    
    return JsonResponse({
        'success': True,
        'districts': districts_data
    })


@csrf_exempt
@require_http_methods(["POST"])
@async_view
@admin_required
async def add_staff(request):
    """
    Yangi xodim qo'shish
    
    POST data:
    - user_id: Telegram user ID
    - role: rol (courier, doctor, admin)
    """
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        role = data.get('role', 'user')
        
        if not user_id:
            return JsonResponse({'error': 'user_id required'}, status=400)
        
        try:
            user = await sync_to_async(TelegramUser.objects.get)(user_id=int(user_id))
            
            # Rolni o'zgartirish
            user.role = role
            if role == 'admin':
                user.is_admin = True
            
            await sync_to_async(user.save)(update_fields=['role', 'is_admin'])
            
            return JsonResponse({
                'success': True,
                'message': 'Staff added successfully',
                'staff': {
                    'id': user.id,
                    'user_id': user.user_id,
                    'first_name': user.first_name,
                    'role': user.role,
                }
            })
            
        except TelegramUser.DoesNotExist:
            return JsonResponse({'error': 'User not found in database. User must start the bot first.'}, status=404)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@async_view
@admin_required
async def remove_staff(request):
    """
    Xodimni olib tashlash (rolni 'user' ga o'zgartirish)
    
    POST data:
    - staff_id: xodim ID
    """
    try:
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        
        if not staff_id:
            return JsonResponse({'error': 'staff_id required'}, status=400)
        
        staff = await sync_to_async(TelegramUser.objects.get)(id=staff_id)
        
        staff.role = 'user'
        staff.is_admin = False
        staff.district = None
        
        await sync_to_async(staff.save)(update_fields=['role', 'is_admin', 'district'])
        
        return JsonResponse({
            'success': True,
            'message': 'Staff removed successfully'
        })
        
    except TelegramUser.DoesNotExist:
        return JsonResponse({'error': 'Staff not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@async_view
@admin_required
async def get_staff_stats(request):
    """
    Xodimlar statistikasi
    """
    admins_count = await sync_to_async(
        TelegramUser.objects.filter(role='admin').count
    )()
    
    couriers_count = await sync_to_async(
        TelegramUser.objects.filter(role='courier').count
    )()
    
    doctors_count = await sync_to_async(
        TelegramUser.objects.filter(role='doctor').count
    )()
    
    active_couriers = await sync_to_async(
        TelegramUser.objects.filter(role='courier', is_active=True).count
    )()
    
    couriers_with_district = await sync_to_async(
        TelegramUser.objects.filter(role='courier', district__isnull=False).count
    )()
    
    return JsonResponse({
        'success': True,
        'stats': {
            'total_staff': admins_count + couriers_count + doctors_count,
            'admins': admins_count,
            'couriers': couriers_count,
            'doctors': doctors_count,
            'active_couriers': active_couriers,
            'couriers_with_district': couriers_with_district,
        }
    })
