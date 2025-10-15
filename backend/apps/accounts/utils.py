from django.contrib.auth.tokens import PasswordResetTokenGenerator


# Default Django token generator works fine
token_generator = PasswordResetTokenGenerator()
