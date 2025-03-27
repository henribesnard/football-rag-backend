from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class Role(Base, TimeStampMixin):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)  # Indique si le rôle est un rôle système non modifiable
    
    # Relationships
    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"

class Permission(Base, TimeStampMixin):
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(100), unique=True, nullable=False)  # Code technique unique pour la vérification programmatique
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)  # Pour regrouper les permissions
    
    # Relationships
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")
    
    # Indexes
    __table_args__ = (
        Index('ix_permissions_category', 'category'),
    )
    
    def __repr__(self):
        return f"<Permission(id={self.id}, code='{self.code}')>"

class RolePermission(Base):
    """
    Classe pour accéder directement à la table d'association role_permissions
    avec des fonctionnalités supplémentaires si nécessaire.
    """
    __tablename__ = 'role_permissions'
    
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(Integer, ForeignKey('permissions.id'), primary_key=True)
    granted_at = Column(String(50), nullable=True)
    
    # Relationships
    role = relationship("Role")
    permission = relationship("Permission")
    
    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"