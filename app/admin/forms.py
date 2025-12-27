from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField, SelectField, PasswordField, \
    SelectMultipleField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Email, ValidationError, Regexp
from sqlalchemy import select
from app import db

from app.models import DormBuilding, User


class SparePartForm(FlaskForm):
    """
    配件管理表单：用于新增配件或编辑配件基本信息
    """
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
        Optional(),  # 编辑时允许为空(代表不改)，新增时默认为0
        NumberRange(min=0, message='库存不能为负数')
    ])
    submit = SubmitField('保存配件信息')


class StockInForm(FlaskForm):
    """
    快速补货表单：用于入库操作
    """
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
    """
    删除表单：用于删除操作（仅用于CSRF保护）
    """
    pass


class UserFormMixin:
    """
    用户表单共用字段与逻辑
    """
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

    # 宿舍楼与房间号 (初始choices为空，在__init__中动态加载)
    building_id = SelectField('所属宿舍楼', coerce=int, validators=[Optional()])
    room_no = StringField('房间号', validators=[Optional(), Length(max=10)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 动态加载所有楼宇，用于下拉框
        # 注意：这里需要应用上下文，确保在视图函数中实例化表单时数据库连接正常
        try:
            stmt = select(DormBuilding).order_by(DormBuilding.building_name)
            buildings = db.session.execute(stmt).scalars().all()

            self.building_id.choices = [(0, '--- 不绑定宿舍 ---')] + \
                                       [(b.building_id, b.building_name) for b in buildings]
        except Exception:
            self.building_id.choices = [(0, '--- 数据库连接错误 ---')]

    def validate_room_no(self, field):
        """
        自定义校验：如果角色是学生，则必须填写房间号
        """
        # 注意：self.role.data 获取的是提交的数据(String)
        if self.role.data == 'Student' and not field.data:
            raise ValidationError('选择“学生”角色时，必须填写房间号。')

    def validate_building_id(self, field):
        """
        自定义校验：如果角色是学生，必须选择有效的宿舍楼
        """
        if self.role.data == 'Student' and (field.data == 0 or field.data is None):
            raise ValidationError('选择“学生”角色时，必须绑定宿舍楼。')


class UserCreateForm(UserFormMixin, FlaskForm):
    """
    管理员新增用户表单
    """
    account = StringField('登录账号（学号/工号）', validators=[
        DataRequired(message='请输入账号'),
        Length(min=4, max=50, message='账号长度4-50字符'),
        Regexp(r'^[a-zA-Z0-9_]+$', message='账号只能包含字母、数字和下划线')
    ])

    # 新增时密码可选，如果不填则在View层设为默认密码 (如123456)
    password = PasswordField('登录密码', validators=[
        Optional(),
        Length(min=6, message='密码长度至少6位')
    ], render_kw={"placeholder": "留空则使用默认密码: 123456"})

    submit = SubmitField('创建用户')

    def validate_account(self, field):
        """校验账号是否已存在"""
        stmt = select(User).where(User.account == field.data)
        if db.session.execute(stmt).scalars().first():
            raise ValidationError('该账号已存在，请更换。')

    def validate_email(self, field):
        """校验邮箱是否已存在"""
        if field.data:
            stmt = select(User).where(User.email == field.data)
            if db.session.execute(stmt).scalars().first():
                raise ValidationError('该邮箱已被注册。')


class UserEditForm(UserFormMixin, FlaskForm):
    """
    管理员编辑用户表单
    注意：账号通常不允许修改，故不包含 account 字段
    """
    status = SelectField('账号状态', choices=[
        (1, '正常 (Active)'),
        (0, '禁用 (Inactive)')
    ], coerce=int, validators=[DataRequired()])

    submit = SubmitField('更新用户信息')

    def __init__(self, original_user_id, *args, **kwargs):
        """
        初始化时传入 user_id，用于排除自身的唯一性检查
        """
        super().__init__(*args, **kwargs)
        self.original_user_id = original_user_id

    def validate_email(self, field):
        """校验邮箱唯一性（排除自己）"""
        if field.data:
            stmt = select(User).where(User.email == field.data)
            user = db.session.execute(stmt).scalars().first()

            if user and user.user_id != self.original_user_id:
                raise ValidationError('该邮箱已被其他用户占用。')


class DispatchForm(FlaskForm):
    """
    派单表单：管理员将工单指派给维修工（支持多选）
    """
    # 1. 改为 SelectMultipleField，名称改为复数 worker_ids
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

            # 生成选项列表
            choices = [(w.user_id, f"{w.username} ({w.account})") for w in workers]
            self.worker_ids.choices = choices

        except Exception:
            self.worker_ids.choices = []

    # 2. 修改校验逻辑，检查列表是否为空
    def validate_worker_ids(self, field):
        if not field.data or len(field.data) == 0:
            raise ValidationError('请至少选择一位维修人员。')