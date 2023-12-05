from datetime import datetime, timedelta
from typing import List

from sqlalchemy.future import select
from sqlalchemy import text, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi_limiter.depends import RateLimiter

from app.database.db import get_db
from app.database.model import Contact,User
from app.schemas import ContactModel,ContactResponse
from app.services.auth import auth_service


router = APIRouter(prefix='/main', tags=["contacts"])

async def get_contacts(skip: int, limit: int, user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Contact).filter(Contact.user_id == user_id).offset(skip).limit(limit)
    )
    contacts = result.scalars().all()
    return contacts


@router.get("/", response_model=List[ContactResponse], description='No more than 10 requests per minute',
            dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def read_notes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(auth_service.get_current_user)):
    contacts = await get_contacts(skip, limit, current_user, db)
    return contacts


@router.get("/api/healthchecker")
async def healthchecker(db: AsyncSession = Depends(get_db)):
    try:
        result0 = await db.execute(text("SELECT 1"))
        result1 = result0.fetchone()
        if result1 is None:
            raise HTTPException(status_code=500, detail="Database is not configured correctly")
        return {"message": "Welcome to FastAPI!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error connecting to the database")


@router.post("/contact", response_model = ContactResponse)
async def add_contact(body :ContactModel, db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    contact_email = await  db.execute(select(Contact).filter(Contact.email == body.email))
    existing_email = contact_email.fetchone()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is exsisting",
        )
    contact_phone= await db.execute(select(Contact).filter(Contact.phone == body.phone))
    existing_phone = contact_phone.fetchone()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone is exsisting",
        )
    contact=Contact(name=body.name, email=body.email,surname=body.surname,
                    phone=body.phone,birthday=body.birthday,notes=body.notes,
                    user_id=user.id)

    db.add(contact)
    await  db.commit()

    raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail="created were Successful",
        )


@router.get("/contacts", response_model = List[ContactResponse])
async def all_contacts(db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    result = await db.execute(select(Contact).filter(Contact.user_id == user.id))
    contacts = result.scalars().all()
    
    contact_responses = []
    for contact in contacts:
        contact_response = ContactResponse(
            id=contact.id,
            name=contact.name,
            surname=contact.surname,
            email=contact.email,
            phone=contact.phone,
            birthday=contact.birthday,
            notes=contact.notes,
        )
        contact_responses.append(contact_response)

    return contact_responses


@router.put("/contact/{contact_id}", response_model = ContactResponse)
async def update(contact_id : int,body:ContactModel,db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    result = await db.execute(select(Contact).filter(Contact.user_id == user.id, Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    
    if contact:
        contact.name = body.name
        contact.surname = body.surname
        contact.phone = body.phone
        contact.notes = body.notes
        contact.birthday = body.birthday
        await db.commit()
        await db.refresh(contact)
        
    contact_response = ContactResponse.model_validate(contact)
    return contact_response


@router.get("/contact/{elem}", response_model = List[ContactResponse])
async def search(elem : str,db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    result = await db.execute(
        select(Contact).filter(
            and_(
                Contact.user_id == user.id,
                or_(
                    Contact.name.ilike(f"%{elem}%"),
                    Contact.surname.ilike(f"%{elem}%"),
                    Contact.email.ilike(f"%{elem}%"),
                )
            )
        )
    )
    contacts = result.scalars().all()
    if len(contacts)==0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NOT FOUND",
        )
    return contacts


@router.delete("/contact/{contact_id}")
async def Delete(contact_id : int,db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    result= await db.execute(select(Contact).filter(Contact.user_id == user.id,Contact.id==contact_id))
    contact = result.scalar()
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NOT FOUND",
        )
    await db.delete(contact)
    await db.commit()
    return {"message": "Contact deleted successfully"}



@router.get("/contacts/HB", response_model = List[ContactResponse])
async def HpB(db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    current_date = datetime.now().date()
    end_date = current_date + timedelta(days=7)


    result = await db.execute(select(Contact).filter(and_(
            Contact.user_id==user.id,
            func.extract('month', Contact.birthday) >= current_date.month,
            func.extract('day', Contact.birthday) >= current_date.day,
            func.extract('day', Contact.birthday) <= end_date.day
        )
    ))
    contact = result.scalars().all()

    return contact