from apartment.elastic.documents import ApartmentDocument


def get_apartments(project_uuid=None):
    search = ApartmentDocument.search()

    # Filters
    if project_uuid:
        search = search.filter("term", project_uuid__keyword=project_uuid)

    # Exclude project fields
    search = search.source(excludes=["project_*"])

    # Get all items
    count = search.count()
    response = search[0:count].execute()

    return response


def get_projects(project_uuid=None):
    search = ApartmentDocument.search()

    # Filters
    if project_uuid:
        search = search.filter("term", project_uuid__keyword=project_uuid)

    # Project data needs to exist in apartment data
    search = search.filter("exists", field="project_id")

    # Get only most recent apartment which has project data
    search = search.extra(
        collapse={
            "field": "project_id",
            "inner_hits": {
                "name": "most_recent",
                "size": 1,
                "sort": [{"project_id": "desc"}],
            },
        }
    )

    # Retrieve only project fields
    search = search.source(["project_*"])

    # Get all items
    count = search.count()
    response = search[0:count].execute()

    return response