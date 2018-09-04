# django-unchained
This is Django, without chains!

Ever needed a specific development environment for your Django project? Hopefully `django-unchained`, formally `django-on-steroids`, will streamline your development workflow.

**Specialised Management Commands**:

`$ python manage.py runserver` becomes `$ python manage.py runsecureserver` (this will run you site in a secure SSL environment)

**Bundled Middleware Classes**:

`CrossOriginResourceSharingMiddleware` (this will allow `POST`, `UPDATE`, `DELETE` and `PUT` methods to be accessible from your project's API, allowing a Django an off the shelf Django headless experience.
