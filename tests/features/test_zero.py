from pytest_bdd import scenario, given, when, then


@scenario('zero.feature', 'Factorial of a number',
          example_converters=dict(number=float, result=float))
def test_zero():
    """Simple test for BDD"""
    pass


@given('I have the <number>')
def number(number):
    """I have the number, argument for the factorial function"""
    pass


@given('I have the <result>')
def result(result):
    """I have the result as specified"""
    pass


@then('I see the result is equal to <result>')
def have(result, number):
    """I have the result from the BDD specs, to be compared
    with the actual computation"""
    assert result == factorial(number)


@when('I compute it')
def compute_stub():
    pass

    
def factorial(number):
    """Computes the factorial"""
    number = int(number)
    if (number == 0) or (number == 1):
        return 1
    else:
        return number * factorial(number-1)
