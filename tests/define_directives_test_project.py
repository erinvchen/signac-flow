import datetime

from flow import FlowProject


class _DirectivesTestProject(FlowProject):
    pass


group = _DirectivesTestProject.make_group(name="walltimegroup")


@_DirectivesTestProject.operation.with_directives({"walltime": 1.0})
@group
def op_walltime(job):
    pass


@_DirectivesTestProject.operation.with_directives({"walltime": None})
@group
def op_walltime_2(job):
    pass


@_DirectivesTestProject.operation.with_directives(
    {"walltime": datetime.timedelta(hours=2)}
)
@group
def op_walltime_3(job):
    pass


if __name__ == "__main__":
    _DirectivesTestProject().main()
