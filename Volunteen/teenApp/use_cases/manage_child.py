from teenApp.entities.child import Child

class ManageChild:
    def __init__(self, child_repo):
        self.child_repo = child_repo

    def add_points(self, identifier, points):
        try:
            child = self.child_repo.get_child_by_identifier(identifier)
            child.add_points(points)
        except Child.DoesNotExist:
            raise ValueError(f"Child with identifier {identifier} does not exist.")
    
    def subtract_points(self, identifier, points):
        try:
            child = self.child_repo.get_child_by_identifier(identifier)
            child.subtract_points(points)
        except Child.DoesNotExist:
            raise ValueError(f"Child with identifier {identifier} does not exist.")
