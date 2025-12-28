from flask_wtf import FlaskForm
from wtforms import TextAreaField, DateTimeLocalField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError


class StartRepairForm(FlaskForm):
    """
    开始维修确认表单
    用途：工人点击“开始维修”按钮，将工单状态由 Assigned -> InProgress
    """
    submit = SubmitField('开始维修')


class MaintenanceReportForm(FlaskForm):
    """
    维修完工填报表单
    用途：填写维修记录核心字段，耗材部分由前端动态生成，后端直接获取
    """
    start_time = DateTimeLocalField(
        '实际开始时间',
        # HTML5 datetime-local 传回的格式通常是 %Y-%m-%dT%H:%M
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired(message="请输入开始时间")]
    )
    end_time = DateTimeLocalField(
        '实际完成时间',
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired(message="请输入完成时间")]
    )
    result_desc = TextAreaField(
        '维修结果描述',
        validators=[
            DataRequired(message="请填写维修结果描述"),
            Length(min=5, max=500, message="描述长度需要在5-500字之间")
        ],
        render_kw={"rows": 4, "placeholder": "请详细描述故障原因及维修措施..."}
    )

    submit = SubmitField('提交完工')

    def validate_end_time(self, field):
        """自定义验证：结束时间必须晚于开始时间"""
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError('结束时间必须晚于开始时间')