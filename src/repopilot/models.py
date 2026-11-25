from pydantic import BaseModel, Field

class FileInfo(BaseModel):
    path: str
    name: str
    extension: str

class SearchResult(BaseModel):
    file: str
    line_number: int = Field(ge=1)
    content: str

class DependencyFile(BaseModel):
    path: str
    ecosystem: str

class EntryPoint(BaseModel):
    path: str
    reason: str
    line_number: int | None = None

class RepositoryAnalysis(BaseModel):
    name: str
    root: str

    directories: list[str] = Field(default_factory=list)
    files: list[FileInfo] = Field(default_factory=list)

    readme_path: str | None = None
    readme_content: str | None = None

    dependency_files: list[DependencyFile] = Field(
        default_factory=list
    )

    entry_points: list[EntryPoint] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(default_factory=list)