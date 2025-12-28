from crypt import methods

from flask import render_template, request, current_app, flash, redirect, url_for
from sqlalchemy import select, or_


from app import db
from app.admin import bp
from app.decorators import admin_required
from app.models import SparePart, PartUsageDetail
from app.admin.forms import StockInForm, SparePartForm, DeleteForm


@bp.route('/inventory')
@admin_required
def inventory():
    """
    库存列表页
    包含：分页、搜索、预警高亮排序
    """
    stmt = select(SparePart)

    is_low_stock = (SparePart.current_stock < SparePart.warning_line)
    stmt = stmt.order_by(is_low_stock.desc(), SparePart.part_id.desc())

    parts = db.session.execute(stmt).scalars().all()

    stock_in_form = StockInForm()
    delete_form = DeleteForm()

    return render_template(
        'admin/inventory/list.html',
        parts=parts,
        stock_in_form=stock_in_form,
        delete_form=delete_form,
        posts_per_page=current_app.config.get('POSTS_PER_PAGE', 10)
    )


@bp.route('/inventory/add', methods=['GET', 'POST'])
@admin_required
def add_part():
    """新增配件"""
    form = SparePartForm()

    if form.validate_on_submit():
        part = SparePart(
            part_name=form.part_name.data,
            spec=form.spec.data,
            unit=form.unit.data,
            price=form.price.data,
            warning_line=form.warning_line.data,
            current_stock=form.current_stock.data if form.current_stock.data else 0
        )
        try:
            db.session.add(part)
            db.session.commit()
            flash(f'配件 "{part.part_name}" 添加成功', 'success')
            return redirect(url_for('admin.inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败：{str(e)}', 'danger')

    return render_template('admin/inventory/edit.html', form=form, title='新增配件')


@bp.route('/inventory/edit/<int:part_id>', methods=['GET', 'POST'])
@admin_required
def edit_part(part_id):
    """编辑配件基本信息"""

    part = db.session.get(SparePart, part_id)
    if not part:
        flash('未找到该配件', 'danger')
        return redirect(url_for('admin.inventory'))

    form = SparePartForm(obj=part)

    if form.validate_on_submit():
        try:
            part.part_name = form.part_name.data
            part.spec = form.spec.data
            part.unit = form.unit.data
            part.price = form.price.data
            part.warning_line = form.warning_line.data
            part.current_stock = form.current_stock.data

            db.session.commit()
            flash('配件信息更新成功', 'success')
            return redirect(url_for('admin.inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'danger')

    return render_template('admin/inventory/edit.html', form=form, title='编辑配件', part=part)


@bp.route('/inventory/stock_in/<int:part_id>', methods=['POST'])
@admin_required
def stock_in(part_id):
    """
    快速补货/入库
    通常由列表页的 Modal 提交 POST 请求触发
    """
    form = StockInForm()

    if form.validate_on_submit():
        part = db.session.get(SparePart, part_id)
        if not part:
            flash('配件不存在', 'danger')
            return redirect(url_for('admin.inventory'))

        try:
            add_qty = form.add_quantity.data
            new_price = form.new_price.data

            part.current_stock += add_qty

            if new_price is not None:
                part.price = new_price

            db.session.commit()
            flash(f'补货成功！{part.part_name} 库存 +{add_qty}', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'操作失败：{str(e)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'补货失败：{error}', 'danger')

    return redirect(url_for('admin.inventory'))

@bp.route('/inventory/delete/<int:part_id>', methods=['POST'])
@admin_required
def delete_part(part_id):
    """删除配件"""
    form = DeleteForm()
    if not form.validate_on_submit():
        flash('删除操作失败：表单验证错误', 'danger')
        return redirect(url_for('admin.inventory'))
    
    part = db.session.get(SparePart, part_id)
    if not part:
        flash('配件不存在', 'danger')
        return redirect(url_for('admin.inventory'))

    stmt = select(PartUsageDetail).where(PartUsageDetail.part_id == part_id).limit(1)
    is_used = db.session.execute(stmt).first()

    if is_used:
        flash(f'无法删除配件 "{part.part_name}"，因为存在关联的历史维修记录。', 'warning')
        # 这里未来可以扩展为 "逻辑删除" 或 "停用"
        return redirect(url_for('admin.inventory'))

    try:
        db.session.delete(part)
        db.session.commit()
        flash('配件已删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'danger')

    return redirect(url_for('admin.inventory'))

