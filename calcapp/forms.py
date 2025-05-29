from django import forms

class CalcForm(forms.Form):
    num1 = forms.FloatField(label='First Number')
    num2 = forms.FloatField(label='Second Number')
    operation = forms.ChoiceField(
        choices=[
            ('add', 'Add'),
            ('subtract', 'Subtract'),
            ('multiply', 'Multiply'),
            ('divide', 'Divide'),
        ],
        label='Operation'
    )

class TaskForm(forms.Form):
    description = forms.CharField(max_length=255, label='Task Description')

class CurrencyForm(forms.Form):
    amount = forms.FloatField(label='Amount', min_value=0.01)
    from_currency = forms.ChoiceField(
        label='From Currency',
        choices=[
            ('USD', 'US Dollar'),
            ('EUR', 'Euro'),
            ('GBP', 'British Pound'),
            ('JPY', 'Japanese Yen'),
            ('CAD', 'Canadian Dollar'),
            ('AUD', 'Australian Dollar'),
            ('INR', 'Indian Rupee'),
            ('NGN', 'Nigerian Naira'),
        ]
    )
    to_currency = forms.ChoiceField(
        label='To Currency',
        choices=[
            ('USD', 'US Dollar'),
            ('EUR', 'Euro'),
            ('GBP', 'British Pound'),
            ('JPY', 'Japanese Yen'),
            ('CAD', 'Canadian Dollar'),
            ('AUD', 'Australian Dollar'),
            ('INR', 'Indian Rupee'),
            ('NGN', 'Nigerian Naira'),
        ]
    )