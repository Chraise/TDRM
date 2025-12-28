from flask import render_template, request, flash, redirect, url_for
from sqlalchemy import select, func, and_
from app import db
from app.admin import bp
from app.decorators import admin_required
from app.models import DormBuilding, User, RepairOrder, OrderStatus
from app.admin.forms import BuildingForm, DeleteForm


@bp.route('/building')
@admin_required
def building_list():
    """宿舍楼列表：包含用户数和活跃工单统计"""
    user_count_subquery = (
        select(func.count(User.user_id))
        .where(User.building_id == DormBuilding.building_id)
        .correlate(DormBuilding)
        .scalar_subquery()
    )

    active_order_count_subquery = (
        select(func.count(RepairOrder.order_id))
        .where(
            and_(
                RepairOrder.repair_building_id == DormBuilding.building_id,
                RepairOrder.status != OrderStatus.COMPLETED,
                RepairOrder.status != OrderStatus.CANCELLED
            )
        )
        .correlate(DormBuilding)
        .scalar_subquery()
    )

    stmt = (
        select(
            DormBuilding,
            user_count_subquery.label('user_count'),
            active_order_count_subquery.label('active_order_count')
        )
        .order_by(DormBuilding.building_name)
    )

    result = db.session.execute(stmt).all()

    buildings_with_stats = [
        {
            'building': row[0],
            'user_count': row.user_count or 0,
            'active_order_count': row.active_order_count or 0
        }
        for row in result
    ]

    delete_form = DeleteForm()

    return render_template('admin/building/list.html',
                           buildings_with_stats=buildings_with_stats,
                           delete_form=delete_form)


@bp.route('/building/create', methods=['GET', 'POST'])
@admin_required
def building_create():
    """创建新楼宇"""
    form = BuildingForm()

    if form.validate_on_submit():
        try:
            new_building = DormBuilding(
                building_name=form.building_name.data,
                location=form.location.data,
                admin_contact=form.admin_contact.data
            )

            db.session.add(new_building)
            db.session.commit()

            flash(f'宿舍楼 "{new_building.building_name}" 创建成功', 'success')
            return redirect(url_for('admin.building_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'danger')

    return render_template('admin/building/form.html', form=form, title='新增宿舍楼')


@bp.route('/building/edit/<int:building_id>', methods=['GET', 'POST'])
@admin_required
def building_edit(building_id):
    """编辑楼宇信息"""
    building = db.session.get(DormBuilding, building_id)
    if not building:
        flash('楼宇不存在', 'danger')
        return redirect(url_for('admin.building_list'))

    form = BuildingForm(original_building_id=building.building_id, obj=building)

    if form.validate_on_submit():
        try:
            form.populate_obj(building)
            db.session.commit()

            flash(f'宿舍楼 "{building.building_name}" 信息已更新', 'success')
            return redirect(url_for('admin.building_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'danger')

    return render_template('admin/building/form.html', form=form, title='编辑宿舍楼', building=building)


@bp.route('/building/delete/<int:building_id>', methods=['POST'])
@admin_required
def building_delete(building_id):
    """删除楼宇：检查关联数据后执行"""
    form = DeleteForm()
    if not form.validate_on_submit():
        flash('删除操作失败：表单验证错误', 'danger')
        return redirect(url_for('admin.building_list'))

    building = db.session.get(DormBuilding, building_id)
    if not building:
        flash('楼宇不存在', 'danger')
        return redirect(url_for('admin.building_list'))

    building_name = building.building_name

    repair_order_stmt = select(func.count(RepairOrder.order_id)).where(
        RepairOrder.repair_building_id == building_id
    )
    repair_order_count = db.session.scalar(repair_order_stmt) or 0

    if repair_order_count > 0:
        flash(f'无法删除楼宇 "{building_name}"，因为存在关联的报修单记录。', 'danger')
        return redirect(url_for('admin.building_list'))

    user_stmt = select(func.count(User.user_id)).where(
        User.building_id == building_id
    )
    user_count = db.session.scalar(user_stmt) or 0

    if user_count > 0:
        flash(f'无法删除楼宇 "{building_name}"，因为仍有 {user_count} 位学生绑定到此楼宇。请先将学生迁移到其他楼宇后再删除。', 'danger')
        return redirect(url_for('admin.building_list'))

    try:
        db.session.delete(building)
        db.session.commit()
        flash(f'楼宇 "{building_name}" 已删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'danger')

    return redirect(url_for('admin.building_list'))

