from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms import StringField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional

class RepairOrderForm(FlaskForm):
    """学生报修表单"""

    repair_building_id = HiddenField('故障所在楼宇ID')
    building_name = StringField(
        '故障所在楼宇',
        render_kw={
            'readonly': True, # 只读！
            'style': 'background-color: #e9ecef; cursor: not-allowed;' # 灰色背景示意不可点
        }
    )
    repair_location = StringField(
        '故障位置（房间号）',
        validators=[
            DataRequired(message="请输入故障位置"),
            Length(max=10, message="故障位置不能超过10个字符")
        ],
        render_kw={'placeholder': '例如：101、201、或1楼洗衣机'}
    )
    title = StringField(
        '报修主题',
        validators=[
            DataRequired(message="请输入报修主题"),
            Length(max=100, message="报修主题不能超过100个字符")
        ],
        render_kw={'placeholder': '简要描述故障类型，如：水龙头漏水、电灯不亮等'}
    )
    description = TextAreaField(
        '详细描述',
        validators=[
            Optional(),
            Length(max=1000, message="详细描述不能超过1000个字符")
        ],
        render_kw={
            'rows': 5,
            'placeholder': '请详细描述故障情况，包括发生时间、具体位置、影响范围等（选填）'
        }
    )
    image_urls = MultipleFileField(
        '故障图片',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif'], message='只允许上传图片文件')
        ],
        render_kw={'accept': 'image/*'},
        description='可以上传多张图片（选填）'
    )
    submit = SubmitField('提交报修')

    def __init__(self, *args, **kwargs):
        repair_building_id = kwargs.pop('building_id', None)
        repair_location = kwargs.pop('repair_location', None)
        building_name = kwargs.pop('building_name', None)

        super(RepairOrderForm, self).__init__(*args, **kwargs)

        if repair_building_id is not None:
            self.repair_building_id.data = repair_building_id
        if building_name is not None:
            self.building_name.data = building_name
        if not self.is_submitted(): # 这个设计可以保留用户输入的数据，而不会被刷新掉
            if repair_location is not None:
                self.repair_location.data = repair_location
