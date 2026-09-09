from pathlib import Path

from app.analyzers.java_spring_analyzer import JavaSpringProjectAnalyzer


def test_spring_analyzer_extracts_endpoints_and_calls() -> None:
    root = Path(__file__).parents[1] / "fixtures" / "spring_sample"
    files = [path.relative_to(root).as_posix() for path in root.rglob("*.java")]

    result = JavaSpringProjectAnalyzer().analyze(root=root, files=files)

    assert {
        (endpoint["http_method"], endpoint["path"]) for endpoint in result.endpoints.endpoints
    } == {
        ("GET", "/api/users/{id}"),
        ("POST", "/api/users"),
    }
    get_endpoint = next(
        endpoint for endpoint in result.endpoints.endpoints if endpoint["http_method"] == "GET"
    )
    assert get_endpoint["parameters"][0]["location"] == "PATH"
    assert get_endpoint["summary"] == "Return one user."
    assert get_endpoint["module_name"] == "User"
    assert get_endpoint["extra_metadata"]["category"] == "User"
    assert get_endpoint["extra_metadata"]["businessSteps"]
    assert "UserService.findUser()" in get_endpoint["extra_metadata"]["businessLogic"]

    node_types = {node["node_type"] for node in result.graph.nodes.values()}
    assert {"API", "ROUTE_FUNCTION", "SERVICE", "REPOSITORY"} <= node_types
    relations = {
        (
            result.graph.nodes[relation["source_key"]]["name"],
            result.graph.nodes[relation["target_key"]]["name"],
        )
        for relation in result.graph.relations.values()
        if relation["relation_type"] == "CALLS"
    }
    assert ("getUser", "findUser") in relations
    assert ("findUser", "selectById") in relations


def test_spring_analyzer_deduplicates_copied_sources() -> None:
    root = Path(__file__).parents[1] / "fixtures" / "spring_sample"
    files = [path.relative_to(root).as_posix() for path in root.rglob("*.java")]
    files.append(next(path for path in files if path.endswith("UserController.java")))

    result = JavaSpringProjectAnalyzer().analyze(root=root, files=files)
    identities = [
        (
            endpoint["http_method"],
            endpoint["path"],
            endpoint["qualified_name"],
        )
        for endpoint in result.endpoints.endpoints
    ]

    assert len(identities) == len(set(identities))
