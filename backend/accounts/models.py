from django.db import models


class StaffMember(models.Model):
    """People who share the tracker's single login. Each picks their name in
    the app ("Who's working?") and their edits are recorded under it."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


def staff_names():
    return list(StaffMember.objects.values_list("name", flat=True))
