from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField, SelectField, PasswordField, \
    SelectMultipleField, DateField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Email, ValidationError, Regexp
from sqlalchemy import select
from app import db

from app.models import DormBuilding, User


class SparePartForm(FlaskForm):
    """配件管理表单"""
    part_name = StringField('配件名称', validators=[
        DataRequired(message='请输入配件名称'),
        Length(max=100, message='名称长度不能超过100个字符')
    ])
    spec = StringField('规格型号', validators=[
        Optional(),
        Length(max=50, message='规格长度不能超过50个字符')
    ])
    unit = StringField('单位', validators=[
        Optional(),
        Length(max=10, message='单位长度不能超过10个字符')
    ], render_kw={"placeholder": "如：个、米、升"})
    price = DecimalField('单价 (元)', places=2, validators=[
        DataRequired(message='请输入单价'),
        NumberRange(min=0, message='单价不能为负数')
    ])
    warning_line = IntegerField('库存预警阈值', default=10, validators=[
        DataRequired(),
        NumberRange(min=0, message='预警值不能为负数')
    ], description="当库存低于此数值时，系统会提示补货")
    current_stock = IntegerField('当前库存 / 初始库存', default=0, validators=[
        Optional(),
        NumberRange(min=0, message='库存不能为负数')
    ])
    submit = SubmitField('保存配件信息')


class StockInForm(FlaskForm):
    """快速补货表单"""
    add_quantity = IntegerField('入库数量', validators=[
        DataRequired(message='请输入入库数量'),
        NumberRange(min=1, message='入库数量必须大于0')
    ])
    new_price = DecimalField('最新进货单价 (元)', places=2, validators=[
        Optional(),
        NumberRange(min=0, message='单价不能为负数')
    ], description="留空则保持原价格不变")

    submit = SubmitField('确认入库')


class DeleteForm(FlaskForm):
    """删除表单：仅用于CSRF保护"""
    pass


class UserFormMixin:
    """用户表单共用字段与逻辑"""
    username = StringField('姓名', validators=[
        DataRequired(message='请输入姓名'),
        Length(max=50)
    ])
    role = SelectField('角色', choices=[
        ('Student', '学生'),
        ('Worker', '维修工'),
        ('Admin', '管理员')
    ], validators=[DataRequired()])

    email = StringField('邮箱', validators=[
        Optional(),
        Email(message='请输入有效的邮箱地址')
    ])

    building_id = SelectField('所属宿舍楼', coerce=int, validators=[Optional()])
    room_no = StringField('房间号', validators=[Optional(), Length(max=10)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            stmt = select(DormBuilding).order_by(DormBuilding.building_name)
            buildings = db.session.execute(stmt).scalars().all()

            self.building_id.choices = [(0, '--- 不绑定宿舍 ---')] + \
                                       [(b.building_id, b.building_name) for b in buildings]
        except Exception:
            self.building_id.choices = [(0, '--- 数据库连接错误 ---')]

    def validate_room_no(self, field):
        """学生角色必须填写房间号"""
        if self.role.data == 'Student' and not field.data:
            raise ValidationError('选择"学生"角色时，必须填写房间号。')

    def validate_building_id(self, field):
        """学生角色必须绑定宿舍楼"""
        if self.role.data == 'Student' and (field.data == 0 or field.data is None):
            raise ValidationError('选择"学生"角色时，必须绑定宿舍楼。')


class UserCreateForm(UserFormMixin, FlaskForm):
    """新增用户表单"""
    account = StringField('登录账号（学号/工号）', validators=[
        DataRequired(message='请输入账号'),
        Length(min=4, max=50, message='账号长度4-50字符'),
        Regexp(r'^[a-zA-Z0-9_]+$', message='账号只能包含字母、数字和下划线')
    ])

    password = PasswordField('登录密码', validators=[
        Optional(),
        Length(min=6, message='密码长度至少6位')
    ], render_kw={"placeholder": "留空则使用默认密码: 123456"})

    submit = SubmitField('创建用户')

    def validate_account(self, field):
        """账号唯一性校验"""
        stmt = select(User).where(User.account == field.data)
        if db.session.execute(stmt).scalars().first():
            raise ValidationError('该账号已存在，请更换。')

    def validate_email(self, field):
        """邮箱唯一性校验"""
        if field.data:
            stmt = select(User).where(User.email == field.data)
            if db.session.execute(stmt).scalars().first():
                raise ValidationError('该邮箱已被注册。')


class UserEditForm(UserFormMixin, FlaskForm):
    """编辑用户表单：账号不可修改"""
    status = SelectField('账号状态', choices=[
        (1, '正常 (Active)'),
        (0, '禁用 (Inactive)')
    ], coerce=int, validators=[DataRequired()])

    submit = SubmitField('更新用户信息')

    def __init__(self, original_user_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_user_id = original_user_id

    def validate_email(self, field):
        """邮箱唯一性校验：排除当前用户"""
        if field.data:
            stmt = select(User).where(User.email == field.data)
            user = db.session.execute(stmt).scalars().first()

            if user and user.user_id != self.original_user_id:
                raise ValidationError('该邮箱已被其他用户占用。')


class DispatchForm(FlaskForm):
    """派单表单：支持多选维修工"""
    worker_ids = SelectMultipleField('选择维修师傅', coerce=int, validators=[
        DataRequired(message='请至少选择一位维修人员')
    ])
    submit = SubmitField('确认派单')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            stmt = select(User).where(
                User.role == 'Worker',
                User.status == 1
            ).order_by(User.username)

            workers = db.session.execute(stmt).scalars().all()

            choices = [(w.user_id, f"{w.username} ({w.account})") for w in workers]
            self.worker_ids.choices = choices

        except Exception:
            self.worker_ids.choices = []

    def validate_worker_ids(self, field):
        if not field.data or len(field.data) == 0:
            raise ValidationError('请至少选择一位维修人员。')


class DashboardFilterForm(FlaskForm):
    """仪表板日期筛选表单"""
    start_date = DateField('开始日期', validators=[Optional()])
    end_date = DateField('结束日期', validators=[Optional()])
    submit = SubmitField('应用筛选')


class BuildingForm(FlaskForm):
    """宿舍楼管理表单"""
    building_name = StringField('楼名', validators=[
        DataRequired(message='请输入楼名'),
        Length(max=50, message='楼名长度不能超过50个字符')
    ])
    location = StringField('地理位置', validators=[
        Optional(),
        Length(max=100, message='地理位置长度不能超过100个字符')
    ])
    admin_contact = StringField('宿管办公室电话', validators=[
        Optional(),
        Length(max=20, message='电话长度不能超过20个字符')
    ])
    submit = SubmitField('保存')

    def __init__(self, original_building_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_building_id = original_building_id

    def validate_building_name(self, field):
        """楼名唯一性校验：编辑时排除当前楼宇"""
        if field.data:
            stmt = select(DormBuilding).where(DormBuilding.building_name == field.data)
            building = db.session.execute(stmt).scalars().first()
            
            if building and (self.original_building_id is None or building.building_id != self.original_building_id):
                raise ValidationError('该楼名已存在，请更换。')