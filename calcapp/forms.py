from django import forms

from .models import Task


FORM_INPUT_CLASS = "form-control app-input"
FORM_SELECT_CLASS = "form-select app-select"


class CalcForm(forms.Form):
    num1 = forms.FloatField(
        label="First Number",
        widget=forms.NumberInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "placeholder": "Enter the first number",
                "step": "any",
            }
        ),
    )
    num2 = forms.FloatField(
        label="Second Number",
        widget=forms.NumberInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "placeholder": "Enter the second number",
                "step": "any",
            }
        ),
    )
    operation = forms.ChoiceField(
        choices=[
            ("add", "Add"),
            ("subtract", "Subtract"),
            ("multiply", "Multiply"),
            ("divide", "Divide"),
        ],
        label="Operation",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["description"]
        widgets = {
            "description": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "placeholder": "Add a task you want to remember",
                }
            )
        }
        labels = {"description": "Task"}


class CurrencyForm(forms.Form):
    amount = forms.FloatField(
        label="Amount",
        min_value=0.01,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "placeholder": "Enter amount",
                "step": "any",
            }
        ),
    )
    from_currency = forms.ChoiceField(
        label="From Currency",
        choices=[
            ("USD", "US Dollar"),
            ("EUR", "Euro"),
            ("GBP", "British Pound"),
            ("JPY", "Japanese Yen"),
            ("CAD", "Canadian Dollar"),
            ("AUD", "Australian Dollar"),
            ("INR", "Indian Rupee"),
            ("NGN", "Nigerian Naira"),
        ],
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    to_currency = forms.ChoiceField(
        label="To Currency",
        choices=[
            ("USD", "US Dollar"),
            ("EUR", "Euro"),
            ("GBP", "British Pound"),
            ("JPY", "Japanese Yen"),
            ("CAD", "Canadian Dollar"),
            ("AUD", "Australian Dollar"),
            ("INR", "Indian Rupee"),
            ("NGN", "Nigerian Naira"),
        ],
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
