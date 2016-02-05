Feature: Compute factorial
  In order to play with BDD
  As beginners
  We'll implement factorial

  Scenario Outline: Factorial of a number
    Given I have the <number>
    And I have the <result>
    When I compute it
    Then I see the result is equal to <result>

    Examples:
    | number |        result |
    |      0 |             1 |
    |      1 |             1 |
    |      2 |             2 |
    |      3 |             6 |
    |      4 |            24 |
    |      5 |           120 |
    |      6 |           720 |
    |      7 |          5040 |
    |      8 |         40320 |
    |      9 |        362880 |
    |     10 |       3628800 |
    |     11 |      39916800 |
    |     12 |     479001600 |
    |     13 |    6227020800 |
    |     14 |   87178291200 |
    |     15 | 1307674368000 |
